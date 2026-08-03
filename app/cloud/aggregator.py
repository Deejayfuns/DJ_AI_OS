class CloudAggregator:

    def __init__(self):

        # global transition knowledge base
        # key: "A->B"
        # value: [scores]
        self.transition_db = {}

    # --------------------------
    # INGEST DATA
    # --------------------------

    def ingest(self, transition_map):

        """
        transition_map:
        {
            "A->B": 80,
            "B->C": 70
        }
        """

        for key, score in transition_map.items():

            if key not in self.transition_db:
                self.transition_db[key] = []

            self.transition_db[key].append(score)

    # --------------------------
    # BUILD GLOBAL MODEL
    # --------------------------

    def build_model(self):

        """
        returns averaged global intelligence
        """

        model = {}

        for key, scores in self.transition_db.items():

            model[key] = {
                "avg_score": sum(scores) / len(scores),
                "samples": len(scores)
            }

        return model

    # --------------------------
    # QUERY ENGINE
    # --------------------------

    def predict(self, a, b):

        key = f"{a}->{b}"

        if key not in self.transition_db:
            return 50  # neutral unknown

        scores = self.transition_db[key]

        return sum(scores) / len(scores)
