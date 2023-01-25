from .model import Election, Candidate, Voter
import math
import datetime

###############################################################################
############################# UTILITARIAN #####################################
###############################################################################

def _utilitarian_fptas(e : Election, per_cost : bool = False) -> set[Candidate]:
    pass


def _utilitarian_by_value(e : Election) -> set[Candidate]:
    maxu = len(self.profile) * max(self.profile[c][v] for c in self.profile for v in self.profile[c])
    ret = {i: {} for i in range(e.budget+1)}
    projects = [None] + [c for c in e.profile]
    score = {c: sum(e.profile[c].values()) for c in e.profile}
    for b in range(e.budget + 1):
        if b % 1000 == 0:
            print(b)
        ret[b][projects[0]] = 0
        for i in range(1, len(projects)):
            if b >= projects[i].cost and ret[b - projects[i].cost][projects[i-1]] + score[projects[i]] > ret[b][projects[i-1]]:
                ret[b][projects[i]] = ret[b - projects[i].cost][projects[i-1]] + score[projects[i]]
            else:
                ret[b][projects[i]] = ret[b][projects[i-1]]
    W = set()
    b = e.budget
    i = len(projects) - 1
    while b > 0 and i > 0:
        if ret[b][projects[i]] > ret[b][projects[i-1]]:
            W.add(projects[i])
            b -= projects[i].cost
        i -= 1
    return W


def _utilitarian_rec(e : Election) -> set[Candidate]:
    print((e, e.budget, len(e.profile)))
    projects = [None] + [c for c in e.profile]
    score = {i: sum(e.profile[projects[i]].values()) for i in range(1, len(projects))}
    ret = {}

    b = e.budget
    i = len(projects) - 1
    q = [(b, i)]
    max_q_size = 0
    while q:
        print(f"{datetime.datetime.now()}: {len(ret)}")
        if len(q) > max_q_size:
            max_q_size = len(q)
            print(len(q))
        b, i = q[-1]
        if i == 0:
            ret[b, i] = 0
            q.pop()
            continue
        if b >= projects[i].cost and (b - projects[i].cost, i-1) not in ret:
            q.append((b - projects[i].cost, i-1))
            continue
        if (b, i-1) not in ret:
            q.append((b, i-1))
            continue
        ret1 = ret[b - projects[i].cost, i-1] + score[i] if b >= projects[i].cost else 0
        ret2 = ret[b, i-1]
        ret[b, i] = max(ret1, ret2)
        q.pop()
    W = set()
    while b > 0 and i > 0:
        if ret[b, i] > ret[b, i-1]:
            W.add(projects[i])
            b -= projects[i].cost
        i -= 1
    return W

def utilitarian(e : Election) -> set[Candidate]:
    return _utilitarian_rec(e)
    # print(f"{datetime.datetime.now()}: {e}, {e.budget}, {len(e.profile)}")
    # ret = {}
    # projects = [None] + [c for c in e.profile]
    # score = {c: sum(e.profile[c].values()) for c in e.profile}
    #
    # q = [e.budget]
    # q_elems = set(q)
    # idx = 0
    #
    # cnt = 0
    # while idx < len(q):
    #     cnt += 1
    #     print(f"{datetime.datetime.now()}: {cnt} {q[idx]}")
    #     for j in range(1, len(projects)):
    #         if q[idx] >= projects[j].cost and (q[idx] - projects[j].cost) not in q_elems:
    #             q.append(q[idx] - projects[j].cost)
    #             q_elems.add(q[idx] - projects[j].cost)
    #     idx += 1
    #
    # q = sorted(q, reverse=True)
    # while q:
    #     b = q.pop()
    #     if (b, projects[0]) in ret:
    #         continue
    #     cnt += 1
    #     if cnt % 1000 == 0:
    #         print(f"{datetime.datetime.now()}: {cnt}")
    #     ret[b, projects[0]] = 0
    #     for i in range(1, len(projects)):
    #         if b >= projects[i].cost and ret[b - projects[i].cost, projects[i-1]] + score[projects[i]] > ret[b, projects[i-1]]:
    #             ret[b, projects[i]] = ret[b - projects[i].cost, projects[i-1]] + score[projects[i]]
    #         else:
    #             ret[b, projects[i]] = ret[b, projects[i-1]]
    # W = set()
    # b = e.budget
    # i = len(projects) - 1
    # while b > 0 and i > 0:
    #     if ret[b, projects[i]] > ret[b, projects[i-1]]:
    #         W.add(projects[i])
    #         b -= projects[i].cost
    #     i -= 1
    # return W


###############################################################################
######################## UTILITARIAN GREEDY ###################################
###############################################################################


def _utilitarian_greedy_internal(e : Election, W : set[Candidate], per_cost : bool = False) -> set[Candidate]:
    costW = sum(c.cost for c in W)
    remaining = set(c for c in e.profile if c not in W)
    if per_cost:
        eval = lambda c : -sum(e.profile[c].values()) / c.cost
    else:
        eval = lambda c : -sum(e.profile[c].values())
    ranked = sorted(remaining, key=eval)
    for c in ranked:
        if costW + c.cost <= e.budget:
            W.add(c)
            costW += c.cost
    return W

def utilitarian_greedy(e : Election, per_cost : bool = False) -> set[Candidate]:
    return _utilitarian_greedy_internal(e, set(), per_cost)


###############################################################################
################# PHRAGMEN'S SEQUENTIAL RULE ##################################
###############################################################################


def _phragmen_internal(e : Election, endow : dict[Voter, float], W : set[Candidate]) -> set[Candidate]:
    payment = {i : {} for i in e.voters}
    remaining = set(c for c in e.profile if c not in W)
    costW = sum(c.cost for c in W)
    cnt = 0
    while True:
        cnt += 1
        print(f"{datetime.datetime.now()}: {cnt}")
        next_candidate = None
        lowest_time = math.inf
        for c in remaining:
            if costW + c.cost <= e.budget:
                time = float(c.cost - sum(endow[i] for i in e.profile[c])) / len(e.profile[c])
                if time < lowest_time:
                    next_candidate = c
                    lowest_time = time
        if next_candidate is None:
            break
        W.add(next_candidate)
        costW += next_candidate.cost
        remaining.remove(next_candidate)
        for i in e.voters:
            if i in e.profile[next_candidate]:
                payment[i][next_candidate] = endow[i]
                endow[i] = 0
            else:
                endow[i] += lowest_time
    return W

def phragmen(e : Election) -> set[Candidate]:
    endow = {i : 0.0 for i in e.voters}
    return _phragmen_internal(e, endow, set())


###############################################################################
####################### METHOD OF EQUAL SHARES ################################
###############################################################################


def _mes_internal(e : Election, real_budget : int = 0) -> (dict[Voter, float], set[Candidate]):
    W = set()
    costW = 0
    remaining = set(c for c in e.profile)
    endow = {i : 1.0 * e.budget / len(e.voters) for i in e.voters}
    rho = {c : c.cost / sum(e.profile[c].values()) for c in e.profile}
    cnt = 0
    while True:
        cnt += 1
        print(f"{datetime.datetime.now()}: {cnt}")
        next_candidate = None
        lowest_rho = math.inf
        for c in sorted(remaining, key=lambda c: rho[c]):
            if rho[c] >= lowest_rho:
                break
            if sum(endow[i] for i in e.profile[c]) >= c.cost:
                supporters_sorted = sorted(e.profile[c], key=lambda i: endow[i] / e.profile[c][i])
                price = c.cost
                util = sum(e.profile[c].values())
                for i in supporters_sorted:
                    if endow[i] * util >= price * e.profile[c][i]:
                        break
                    price -= endow[i]
                    util -= e.profile[c][i]
                rho[c] = price / util
                if rho[c] < lowest_rho:
                    next_candidate = c
                    lowest_rho = rho[c]
        if next_candidate is None:
            break
        else:
            W.add(next_candidate)
            costW += next_candidate.cost
            remaining.remove(next_candidate)
            for i in e.profile[next_candidate]:
                endow[i] -= min(endow[i], lowest_rho * e.profile[next_candidate][i])
            if real_budget: #optimization for 'increase-budget' completions
                if costW > real_budget:
                    return None
    return endow, W

def _is_exhaustive(e : Election, W : set[Candidate]) -> bool:
    costW = sum(c.cost for c in W)
    minRemainingCost = min([c.cost for c in e.profile if c not in W], default=math.inf)
    return costW + minRemainingCost > e.budget

def equal_shares(e : Election, completion : str = None) -> set[Candidate]:
    endow, W = _mes_internal(e)
    if completion is None:
        return W
    if completion == 'binsearch':
        initial_budget = e.budget
        while not _is_exhaustive(e, W): #we keep multiplying budget by 2 to find lower and upper bounds for budget
            b_low = e.budget
            e.budget *= 2
            res_nxt = _mes_internal(e, real_budget=initial_budget)
            if res_nxt is None:
                break
            _, W = res_nxt
        b_high = e.budget
        while not _is_exhaustive(e, W) and b_high - b_low >= 1: #now we perform the classical binary search
            e.budget = (b_high + b_low) / 2.0
            res_med = _mes_internal(e, real_budget=initial_budget)
            if res_med is None:
                b_high = e.budget
            else:
                b_low = e.budget
                _, W = res_med
        e.budget = initial_budget
        return W
    if completion == 'utilitarian_greedy':
        return _utilitarian_greedy_internal(e, W)
    if completion == 'phragmen':
        return _phragmen_internal(e, endow, W)
    if completion == 'add1':
        initial_budget = e.budget
        cnt = 0
        while not _is_exhaustive(e, W):
            e.budget *= 1.01 #max(len(e.voters), 
            cnt += 1
            print(f"ITERATION: {datetime.datetime.now()}: {cnt}")
            res_nxt = _mes_internal(e, real_budget=initial_budget)
            if res_nxt is None:
                break
            _, W = res_nxt
        e.budget = initial_budget
        return W
    assert False, f"""Invalid value of parameter completion. Expected one of the following:
        * 'binsearch',
        * 'utilitarian_greedy',
        * 'phragmen',
        * 'add1',
        * None."""
