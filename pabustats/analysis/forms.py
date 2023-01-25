from django import forms
from .models import VotingRule, VotingRuleMode, Election
from django.conf import settings
from django.forms import HiddenInput

class VotingRuleModeWidget(forms.MultiWidget):

    def __init__(self, attrs={}):
        #attrs_select = attrs.copy().update({"style": "display:None"})
        widgets = (
            #forms.Select(attrs=attrs),
            forms.CheckboxInput(attrs=attrs),
            forms.Select(attrs=attrs),
            forms.Select(attrs=attrs)
        )
        super(VotingRuleModeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        print(value)
        if value:
            print(value.split(':::')[0:2])
            return value.split(':::')[0:2]
        return ['', '']

    def subwidgets(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        return context['widget']['subwidgets']

class VotingRuleModeField(forms.MultiValueField):
    widget = VotingRuleModeWidget

    def __init__(self, **kwargs):
        fields = (
            #forms.ModelChoiceField(queryset=VotingRule.objects.all(), required=False, empty_label="<select a rule>"),
            forms.BooleanField(required=False),
            forms.ChoiceField(choices=[(1, "both districtwise and citywide"), (2, "only districtwise"), (3, "only citywide")], required=False),
            forms.ChoiceField(choices=[(1, "both cost and score utilties"), (2, "only score utilties"), (3, "only cost utilities")], required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)
        self.widget.widgets[1].choices = self.fields[1].widget.choices
        self.widget.widgets[2].choices = self.fields[2].widget.choices
        self.widget.widgets[1].attrs.update({'style': 'display:None'})
        self.widget.widgets[2].attrs.update({'style': 'display:None'})

    def compress(self, values):
        if not values[0]:
            return []
        rule = VotingRule.objects.get(name=self.label)
        if values[1] == '1' and values[2] == '1':
            return list(VotingRuleMode.objects.filter(rule=rule))
        elif values[1] == '1':
            cost_utilities = (values[2] == '3')
            return list(VotingRuleMode.objects.filter(rule=rule, cost_utilities=cost_utilities))
        elif values[2] == '1':
            merged = (values[1] == '3')
            return list(VotingRuleMode.objects.filter(rule=rule, merged=merged))
        else:
            cost_utilities = (values[2] == '3')
            merged = (values[1] == '3')
            return list(VotingRuleMode.objects.filter(rule=rule, merged=merged, cost_utilities=cost_utilities))

class VotingRuleModeCitywideWidget(forms.MultiWidget):

    def __init__(self, attrs={}):
        #attrs_select = attrs.copy().update({"style": "display:None"})
        widgets = (
            #forms.Select(attrs=attrs),
            forms.CheckboxInput(attrs=attrs),
            forms.Select(attrs=attrs)
        )
        super(VotingRuleModeCitywideWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        print(value)
        if value:
            print(value.split(':::')[0:1])
            return value.split(':::')[0:1]
        return ['', '']

    def subwidgets(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        return context['widget']['subwidgets']

class VotingRuleModeCitywideField(forms.MultiValueField):
    widget = VotingRuleModeCitywideWidget

    def __init__(self, **kwargs):
        fields = (
            #forms.ModelChoiceField(queryset=VotingRule.objects.all(), required=False, empty_label="<select a rule>"),
            forms.BooleanField(required=False),
            forms.ChoiceField(choices=[(1, "both cost and score utilties"), (2, "only score utilties"), (3, "only cost utilities")], required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)
        self.widget.widgets[1].choices = self.fields[1].widget.choices
        self.widget.widgets[1].attrs.update({'style': 'display:None'})

    def compress(self, values):
        if not values[0]:
            return []
        rule = VotingRule.objects.get(name=self.label)
        if values[1] == '1':
            return list(VotingRuleMode.objects.filter(rule=rule, merged=True))
        else:
            cost_utilities = (values[1] == '3')
            return list(VotingRuleMode.objects.filter(rule=rule, merged=True, cost_utilities=cost_utilities))

class BaseRuleWidget(forms.MultiWidget):

    def __init__(self, attrs={}):
        #attrs_select = attrs.copy().update({"style": "display:None"})
        widgets = (
            #forms.Select(attrs=attrs),
            forms.Select(attrs=attrs),
            forms.Select(attrs=attrs),
            forms.Select(attrs=attrs)
        )
        super(BaseRuleWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        print(value)
        if value:
            print(value.split(':::')[0:2])
            return value.split(':::')[0:2]
        return ['', '']

    def subwidgets(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        return context['widget']['subwidgets']

class BaseRuleField(forms.MultiValueField):
    widget = BaseRuleWidget

    def __init__(self, **kwargs):
        fields = (
            #forms.ModelChoiceField(queryset=VotingRule.objects.all(), required=False, empty_label="<select a rule>"),
            forms.ModelChoiceField(queryset=VotingRule.objects.all(), required=False, empty_label="<no base rule>"),
            forms.ChoiceField(choices=[(2, "districtwise"), (3, "citywide")], required=False),
            forms.ChoiceField(choices=[(2, "cost utilities"), (3, "score utilities")], required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)
        self.widget.widgets[0].choices = self.fields[0].widget.choices
        self.widget.widgets[1].choices = self.fields[1].widget.choices
        self.widget.widgets[2].choices = self.fields[2].widget.choices
        self.widget.widgets[1].attrs.update({'style': 'visibility:hidden'})
        self.widget.widgets[2].attrs.update({'style': 'visibility:hidden'})

    def compress(self, values):
        if not values[0]:
            return None
        rule = values[0]
        cost_utilities = (values[2] == '2')
        merged = (values[1] == '3')
        return VotingRuleMode.objects.get(rule=rule, merged=merged, cost_utilities=cost_utilities)

class BaseRuleCitywideWidget(forms.MultiWidget):

    def __init__(self, attrs={}):
        widgets = (
            forms.Select(attrs=attrs),
            forms.Select(attrs=attrs)
        )
        super(BaseRuleCitywideWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            print(value.split(':::')[0:1])
            return value.split(':::')[0:1]
        return ['', '']

    def subwidgets(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        return context['widget']['subwidgets']

class BaseRuleCitywideField(forms.MultiValueField):
    widget = BaseRuleCitywideWidget

    def __init__(self, **kwargs):
        fields = (
            forms.ModelChoiceField(queryset=VotingRule.objects.all(), required=False, empty_label="<no base rule>"),
            forms.ChoiceField(choices=[(2, "score utilities"), (3, "cost utilities")], required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)
        self.widget.widgets[0].choices = self.fields[0].widget.choices
        self.widget.widgets[1].choices = self.fields[1].widget.choices
        self.widget.widgets[1].attrs.update({'style': 'visibility:hidden'})

    def compress(self, values):
        if not values[0]:
            return None
        rule = values[0]
        cost_utilities = (values[1] == '3')
        return VotingRuleMode.objects.get(rule=rule, merged=True, cost_utilities=cost_utilities)


class ShowForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ShowForm, self).__init__(*args, **kwargs)
        self.fields['election'] = forms.ModelChoiceField(label="Choose an election:", queryset=Election.objects.all(), initial=0)#required=False, empty_label="<general summary>")
        self.fields['base_rule'] = BaseRuleField(required=False)
        for rule in VotingRule.objects.order_by('name'):
            self.fields[f'rule-{rule.id}'] = VotingRuleModeField(label=f"{rule}", required=False)

class ShowFileForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['election'] = forms.FileField(label="Upload your own file (in Pabulib format):", required=True)
        self.fields['base_rule'] = BaseRuleCitywideField(required=False)
        for rule in VotingRule.objects.order_by('name'):
            self.fields[f'rule-{rule.id}'] = VotingRuleModeCitywideField(label=f"{rule}", required=False)

class UploadForm(forms.Form):
    state = forms.CharField()
    city = forms.CharField()
    year = forms.CharField()

class UploadAllForm(forms.Form):
    uploadAll = HiddenInput()
