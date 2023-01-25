from django.db import models

class Location(models.Model):
    state = models.CharField(max_length=200, help_text="State")
    city = models.CharField(max_length=200, help_text="City")

    def __str__(self):
        return f"{self.state}, {self.city}"


class Election(models.Model):
    location = models.ForeignKey(Location, help_text="Location", on_delete=models.CASCADE)
    year = models.CharField(max_length=200, help_text="Year")
    budget = models.IntegerField(help_text="Budget")
    voters_num = models.IntegerField(help_text="Number of voters")
    score = models.BinaryField(help_text="Aggregated profile (list of projects with their total utility)")
    subunit_weight = models.JSONField(help_text="Weight (number of voters) of each subunit")

    def __str__(self):
        return f"PB in {self.location} ({self.year})"


class VotingRule(models.Model):
    """Model representing a voting rule"""
    name = models.CharField(max_length=200, help_text="Official (displayed) name of the rule")
    function_name = models.CharField(max_length=200, help_text="Name of the rule in pabutools.rules package")
    kwargs = models.JSONField(help_text="Kwargs (i.e., completion in case of MES)")

    def __str__(self):
        return self.name

class VotingRuleMode(models.Model):
    rule = models.ForeignKey(VotingRule, on_delete=models.CASCADE)
    cost_utilities = models.BooleanField(help_text="Whether utilities should be converted to costs or not")
    merged = models.BooleanField(help_text="Whether the rule has been run for whole city or in districts")

    def __str__(self):
        return f'{self.rule} ({"citywide" if self.merged else "districtwise"}, {"cost utilties" if self.cost_utilities else "point utilities"})'


class Simulation(models.Model):
    """Model representing a result of a given election for a given voting rule"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    rule_mode = models.ForeignKey(VotingRuleMode, on_delete=models.CASCADE)
    result = models.BinaryField(help_text="Elected outcome (set of Candidate objects from pabutools.model)")
    voter_cost_utility = models.BinaryField(null=True, help_text="Total cost utility from elected projects for each voter")
    voter_point_utility = models.BinaryField(null=True, help_text="Total point utility from elected projects for each voter")
    voter_strength = models.BinaryField(help_text="Strength of each voter")
    subunit_strength = models.JSONField(help_text="Strength of each subunit")

    def __str__(self):
        return f"Simulation: {self.election}, {rule}{(', merged' if merged else '')}"
