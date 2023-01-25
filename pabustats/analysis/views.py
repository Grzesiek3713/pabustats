from django.shortcuts import render
from .models import Election as ElectionDB, Location, VotingRule, VotingRuleMode, Simulation
from .forms import UploadForm, UploadAllForm, ShowForm, ShowFileForm
import random
import csv
import sys
import os
import io
import math
import pickle
import json
import datetime
from pathlib import Path
from statistics import mean, stdev
from .pabutools import rules as pabutools_rules
from .pabutools.model import Election
from django.conf import settings
import datetime

def _no_polish_letters(s):
    return s.replace('ż', 'z').replace('ó', 'o').replace('ł', 'l').replace('ć', 'c').replace('ę', 'e').replace('ś', 's').replace('ą', 'a').replace('ź', 'z').replace('ń', 'n')

def _print_num(num):
    num = round(num, 2)
    return '{:,}'.format(num).replace(',', '&nbsp;')

def _print_fraction(frac):
    return _print_num(frac*100) + "%"

def _get_elections(state, city, year):
    src = settings.PABULIB_PATH + f"{state}_{city}_{year}*.pb".lower()
    return [Election().read_from_files(str(file)) for file in Path(".").glob(src)]

def _run_rule(rule, e):
    return getattr(pabutools_rules, rule.function_name)(e, **rule.kwargs)

def _print_row(name, data, print=str):
    html = f"<tr>\n<td colspan='4'>{name}</td>\n"
    for rule in data:
        html += f"<td class='num'>{print(data[rule])}</td>\n"
    html += "</tr>\n"
    return html

def _print_title_row(name, id=None):
    id_html = f"id={id}" if id else ""
    return f"<tr {id_html}>\n<td colspan='100%'><strong>{name}</strong></td></tr>\n"

def _print_metric(name, metric, base_rule):
    print(f"{datetime.datetime.now()}: Printing metric {name}")
    ret = _print_title_row(f"METRIC: {name.upper()}")
    ret += _print_row(f"Mean:", {rule: mean(metric[rule].values()) for rule in metric}, print=_print_num)
    ret += _print_row(f"Standard deviation:", {rule: stdev(metric[rule].values()) for rule in metric}, print=_print_num)
    if base_rule:
        better, worse = {rule : 0 for rule in metric}, {rule: 0 for rule in metric}
        for rule in metric:
            if rule != base_rule:
                for i in metric[rule]:
                    if metric[rule][i] > metric[base_rule][i]:
                        better[rule] += 1
                    if metric[rule][i] < metric[base_rule][i]:
                        worse[rule] += 1
        for rule in metric:
            better[rule] *= 100.0 / len(metric[rule])
            worse[rule] *= 100.0 / len(metric[rule])
        ret += _print_row(
            f"Comparison with {base_rule}:",
            {rule: "-" if rule == base_rule else f"for {_print_num(better[rule])}% better, for {_print_num(worse[rule])}% worse" for rule in metric})
    return ret

def _distance(dict1, dict2):
    assert dict1.keys() == dict2.keys()
    squares = [(dict1[p]-dict2[p]) ** 2 for p in dict1]
    return sum(squares) ** .5

def _print_distance_metric(name, deserved, got, details=False):
    print(f"{datetime.datetime.now()}: Printing metric {name}")
    ret = _print_title_row(f"METRIC: {name.upper()}")
    if details:
        for elem in deserved:
            ret += _print_row(f"Strength of {elem} (deserved: {_print_num(deserved[elem])}):", {rule: got[rule][elem] for rule in got}, print=_print_num)
    ret += _print_row(f"Total distance:", {rule: _distance(deserved, got[rule]) for rule in got}, print=_print_num)
    return ret

def _get_voter_point_utility(e, committee):
    point_utility = {i: 0 for i in e.voters}
    for c in committee:
        for i in e.profile[c]:
            point_utility[i] += e.profile[c][i]
    return point_utility

def _get_voter_cost_utility(e, committee):
    utility = {i: 0 for i in e.voters}
    for c in committee:
        for i in e.profile[c]:
            utility[i] += e.profile[c][i] * c.cost
    return utility

def _get_voter_strength(e, committee):
    strength = {i: 0 for i in e.voters}
    for c in committee:
        support = sum(e.profile[c].values())
        for i in e.profile[c]:
            strength[i] += c.cost * e.profile[c][i] / support
    return strength

def _get_voter_assignment_to_subunits(e):
    subunits = {}
    for subunit in e.subunits:
        projects = [c for c in e.profile if c.subunit == subunit]
        subunits[subunit] = set(v for c in projects for v in e.profile[c])

    voter_weight = {}
    for v in e.voters:
        subunits_count = len([subunit for subunit in e.subunits if v in subunits[subunit]])
        if subunits_count > 0:
            voter_weight[v] = 1.0 / subunits_count
    return subunits, voter_weight

def _get_subunit_weight(e, assignment):
    subunits, voter_weight = assignment
    ret = {}
    local_voters_num = sum(voter_weight[v] for v in voter_weight)
    for subunit in subunits:
        voters_subunit_num = sum(voter_weight[v] for v in subunits[subunit])
        for v in subunits[subunit]:
            ret[subunit] = 1.0 * e.budget * voters_subunit_num / local_voters_num
    return ret

def _get_subunit_strength(e, committee, assignment):
    subunits, voter_weight = assignment
    ret = {subunit: 0 for subunit in subunits}
    for c in committee:
        support = sum(voter_weight[v] * e.profile[c][v] for v in e.profile[c].keys() & voter_weight.keys())
        for subunit in subunits:
            for v in subunits[subunit] & e.profile[c].keys():
                ret[subunit] += c.cost * voter_weight[v] * e.profile[c][v] / support
    return ret

def _print_results_table(score, committees):
    table = "<thead>\n<tr>\n<th>Subunit</th><th>Project Name</th><th>Cost</th><th>Score</th>"
    for rule in committees:
        table += f"<th>{rule}</th>"
    table += "\n</tr>\n</thead>\n<tbody>\n"
    for c in sorted(score.keys(), key=lambda c : score[c], reverse=True):
        table += f"""<tr>
            <td>{("" if c.subunit is None else c.subunit)}</td>
            <td>{c.name}</td>
            <td class='num' sorttable_customkey='{c.cost}'>{_print_num(c.cost)}</td>
            <td class='num' sorttable_customkey='{score[c]}'>{_print_num(score[c])}</td>
        """
        for rule in committees:
            if c in committees[rule]:
                table += "<td class='selected rule'>&#10003;</td>\n"
            else:
                table += "<td class='not rule'>&ndash;</td>\n"
        table += "</tr>\n"
    table += "</tbody>\n"
    table += _print_title_row(f"GENERAL STATISTICS", id="statistics")
    table += "<tr>\n<td colspan='4'>Total cost</td>\n"
    for rule in committees:
        total_cost = sum(c.cost for c in committees[rule])
        table += f"<td class='num'>{_print_num(total_cost)}</td>\n"
    table += "</tr>\n"
    table += "<tr>\n<td colspan='4'>Total utility</td>\n"
    for rule in committees:
        utility = sum(score[c] for c in score.keys() & committees[rule])
        table += f"<td class='num'>{_print_num(utility)}</td>\n"
    table += "</tr>\n"
    return table


def _print_summary_table(name, locations, elections_num, rules, vals):
    table = f"<h1>{name}</h1>"
    table += "<table><thead>\n<tr>\n<th>Location</th><th>Number of elections</th>"
    for rule in rules:
        table += f"<th>{rule}</th>"
    table += "\n</tr>\n</thead>\n<tbody>\n"
    for loc in locations:
        table += "<tr>\n"
        table += f"<td>{loc}</td><td>{elections_num[loc]}</td>"
        for rule in rules:
            val_mean = mean(vals[loc, rule])
            val_stdev = 0 if len(vals[loc, rule]) == 1 else stdev(vals[loc, rule])
            table += f"<td>Mean: {val_mean}<br>St. dev.: {val_stdev}</td>"
        table += "</tr>\n"
    table += "</tbody></table>"
    return table

def _print_summary(rules):
    print(f"Preparations..")
    locations = Location.objects.order_by('state', 'city')
    metrics = (
        ("AVERAGE NUMBER OF PROJECTS", "voter_point_utility", mean),
        ("STANDARD DEVIATION OF THE NUMBER OF PROJECTS", "voter_point_utility", stdev),
        ("AVERAGE UTILITY", "voter_cost_utility", mean),
        ("STANDARD DEVIATION OF UTILITY", "voter_cost_utility", stdev),
        ("AVERAGE VOTER'S STRENGTH", "voter_strength", mean),
        ("STANDARD DEVIATION OF VOTER'S STRENGTH", "voter_strength", stdev),
    )
    vals = {metric: {} for metric in metrics}
    election_num = {}
    for loc in locations:
        els = ElectionDB.objects.filter(location = loc)
        election_num[loc] = len(els)
        for rule in rules:
            sims = []
            for e in els:
                try:
                    sims.append(Simulation.objects.get(rule_mode = rule, election = e))
                except:
                    print(f"WARNING: Simulation for rule {rule} and election {e} has not been taken into account")
            for metric in metrics:
                _, metric_attr, fun = metric
                vals[metric][(loc, rule)] = [fun(pickle.loads(getattr(sim, metric_attr)).values()) for sim in sims]
    html = ""
    for metric in metrics:
        name, _, _ = metric
        print(f"Printing table: {name}")
        html += _print_summary_table(name, locations, election_num, rules, vals[metric])
    return html

def _simulation_exists(e_db, e, rule_mode):
    try:
        s = Simulation.objects.get(election = e_db, rule_mode=rule_mode)
        if not s.voter_point_utility or not s.voter_cost_utility:
            committee = pickle.loads(s.result)
            if not s.voter_point_utility:
                s.voter_point_utility = pickle.dumps(_get_voter_point_utility(e, committee))
            if not s.voter_point_utility:
                s.voter_cost_utility = pickle.dumps(_get_voter_cost_utility(e, committee))
            s.save()
        return True
    except Simulation.DoesNotExist:
        return False

def _get_location_or_none(state, city):
    try:
        loc = Location.objects.get(state = state, city = city)
        return loc
    except:
        return None

def _get_election_or_none(state, city, year):
    try:
        loc = _get_location_or_none(state, city)
        if loc:
            return ElectionDB.objects.get(location = loc, year = year)
    except:
        pass
    return None

def _save_simulation(e, e_db, rule_mode, committee, assignment):
    s = Simulation()
    s.result = pickle.dumps(committee)
    s.election = e_db
    s.rule_mode = rule_mode
    s.voter_point_utility = pickle.dumps(_get_voter_point_utility(e, committee))
    s.voter_cost_utility = pickle.dumps(_get_voter_cost_utility(e, committee))
    s.voter_strength = pickle.dumps(_get_voter_strength(e, committee))
    s.subunit_strength = _get_subunit_strength(e, committee, assignment)
    s.save()

def _save_election(e, assignment):
    state = _no_polish_letters(e.info['country'])
    city = _no_polish_letters(e.info['unit'])
    loc = _get_location_or_none(state, city)
    if not loc:
        loc = Location()
        loc.state = state
        loc.city = city
        loc.save()
    e_db = ElectionDB()
    e_db.location = loc
    e_db.year = e.info['instance']
    e_db.budget = e.budget
    e_db.voters_num = len(e.voters)
    e_db.score = pickle.dumps({c: sum(e.profile[c].values()) for c in e.profile})
    e_db.subunit_weight = _get_subunit_weight(e, assignment)
    e_db.save()
    return e_db

def _upload_data(state, city, year):
    list_e = _get_elections(state, city, year)
    e = Election()
    for e_ in list_e:
        e = e.merge(e_)
    assignment = _get_voter_assignment_to_subunits(e)
    e_db = _get_election_or_none(state, city, year)
    if not e_db:
        e_db = _save_election(e, assignment)
    for rule_mode in VotingRuleMode.objects.all():
        print(f"{datetime.datetime.now()}: {rule_mode}")
        if not _simulation_exists(e_db, e, rule_mode):
            if rule_mode.cost_utilities:
                e = e.to_cost_utilities()
            committee = _run_rule(rule_mode.rule, e) if rule_mode.merged else set.union(*[_run_rule(rule_mode.rule, e_) for e_ in list_e])
            if rule_mode.cost_utilities:
                e = e.to_point_utilities()
            _save_simulation(e, e_db, rule_mode, committee, assignment)

def upload(request):
    context = {
        'message': None,
        'form': UploadForm()
    }
    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            state = form.cleaned_data['state']
            city = form.cleaned_data['city']
            year = form.cleaned_data['year']
            _upload_data(state, city, year)
            context['message'] = f"Simulations successfully created for {state}, {city}, {year}\n"
    return render(request, 'upload_form.html', context)

def uploadAll(request):
    context = {
        'message': None,
        'form': UploadAllForm()
    }
    if request.method == 'POST':
        form = UploadAllForm(request.POST)
        if form.is_valid():
            src = settings.PABULIB_PATH + "*.pb"
            message = f"Simulations successfully created for:\n"
            instances = set()
            for file in Path(".").glob(src):
                pieces = file.name.split('_')
                state = pieces[0].capitalize()
                city = pieces[1].capitalize()
                year = pieces[2]
                instances.add((state, city, year))
            for state, city, year in sorted(instances):
                print((state, city, year))
                _upload_data(state, city, year)
                message += f" * {state}, {city}, {year}\n"
            context['message'] = message
    return render(request, 'upload_form.html', context)

def show(request):
    context = {
        'form': ShowForm()
    }
    if request.method == 'POST':
        form = ShowForm(request.POST)
        if form.is_valid():
            e = form.cleaned_data['election']
            base_rule = form.cleaned_data['base_rule']
            rule_modes = []
            for rule in VotingRule.objects.all():
                for rule_mode in form.cleaned_data[f'rule-{rule.id}']:
                    if rule_mode != base_rule:
                        rule_modes.append(rule_mode)
            if base_rule:
                rule_modes = [base_rule] + rule_modes
            if not e:
                context = {'summary': _print_summary(rule_modes)}
                return render(request, 'show_summary.html', context)
            s = {}
            for rule_mode in rule_modes:
                s[rule_mode] = Simulation.objects.get(election = e, rule_mode = rule_mode)
            score = pickle.loads(e.score)
            committees = {rule_mode: pickle.loads(s[rule_mode].result) for rule_mode in rule_modes}
            voter_strength = {rule_mode: pickle.loads(s[rule_mode].voter_strength) for rule_mode in rule_modes}
            subunit_strength = {rule_mode: s[rule_mode].subunit_strength for rule_mode in rule_modes}
            context = {
                'prev': 'show',
                'state': e.location.state,
                'city': e.location.city,
                'year': e.year,
                'voters_num': _print_num(e.voters_num),
                'projects_num': _print_num(len(score)),
                'budget': _print_num(e.budget),
                'results': _print_results_table(score, committees),
                'metric_score_utility': _print_metric("score utility", {rule_mode: pickle.loads(s[rule_mode].voter_point_utility) for rule_mode in rule_modes}, base_rule),
                'metric_cost_utility': _print_metric("cost utility", {rule_mode: pickle.loads(s[rule_mode].voter_cost_utility) for rule_mode in rule_modes}, base_rule),
                'metric_voter_strength': _print_distance_metric("voter's strength", {i: e.budget / e.voters_num for i in list(voter_strength.values())[0]}, voter_strength),
                'metric_subunit_strength': _print_distance_metric("subunit's strength", e.subunit_weight, subunit_strength, details=True),
            }
            return render(request, 'show_table.html', context)
        context['form'] = form
    return render(request, 'show_form.html', context)

def showFile(request):
    context = {
        'form': ShowFileForm()
    }
    if request.method == 'POST':
        form = ShowFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = io.StringIO(form.cleaned_data['election_file'].read().decode('utf-8'))
            e = Election().read_from_file(file)
            base_rule = form.cleaned_data['base_rule']
            rules = []
            for rule in VotingRule.objects.all():
                for rule_mode in form.cleaned_data[f'rule-{rule.id}']:
                    if rule_mode != base_rule:
                        rules.append(rule_mode)
            if base_rule:
                rules = [base_rule] + rules
            score = {c: sum(e.profile[c].values()) for c in e.profile}
            committees = {}
            for rule in rules:
                    if rule.cost_utilities:
                        e = e.to_cost_utilities()
                    print(f"{datetime.datetime.now()}: rule={rule}, cost_utilities={rule.cost_utilities}")
                    committees[rule] = _run_rule(rule.rule, e)
                    if rule.cost_utilities:
                        e = e.to_point_utilities()
            voter_strength = {rule: _get_voter_strength(e, committees[rule]) for rule in rules}
            voters_num = len(e.voters)
            context = {
                'prev': 'showFile',
                'state': e.info['country'],
                'city': e.info['unit'],
                'year': e.info['instance'],
                'voters_num': _print_num(voters_num),
                'projects_num': _print_num(len(score)),
                'budget': _print_num(e.budget),
                'results': _print_results_table(score, committees),
                'metric_score_utility': _print_metric("score utility", {rule: _get_voter_point_utility(e, committees[rule]) for rule in rules}, base_rule),
                'metric_cost_utility': _print_metric("cost utility", {rule: _get_voter_cost_utility(e, committees[rule]) for rule in rules}, base_rule),
                'metric_voter_strength': _print_distance_metric("voter's strength", {i: e.budget / voters_num for i in list(voter_strength.values())[0]}, voter_strength),
            }
            return render(request, 'show_table.html', context)
        context['form'] = form
    return render(request, 'show_form.html', context)

def menu(request):
    return render(request, 'menu.html', {})
