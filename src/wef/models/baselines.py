from wef.features.build import NAIVE
from wef.models.registry import Model


class SeasonalNaive(Model):
    """D1: same hour seven days earlier; W1: same weekday one week earlier."""
    name = "seasonal_naive"
    refit = False

    def predict(self, data, origins):
        return data.matrix(origins, NAIVE[data.horizon])
