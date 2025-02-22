from models import Committee, Constituency


class ElectionCalculator:
    def __init__(self, committees, constituencies):
        self.committees = committees
        self.constituencies = constituencies
        self.pastSupport = self.calculate_past_support()

    def calculate_past_support(self):
        total_mandates = sum(c.size for c in self.constituencies)
        pastSupport = {}
        for party in ['td', 'nl', 'pis', 'konf', 'ko']:
            total_support = sum(c.pastSupport[party] * c.size for c in self.constituencies)
            pastSupport[party] = total_support / total_mandates
        return pastSupport

    def calculate_local_support(self, support, constituency):
        past_support_projection = [
            self.pastSupport.get(committee.id, 0) for committee in self.committees
        ]
        local_past_support = constituency.pastSupport
        local_past_support_projection = [
            local_past_support.get(committee.id, 0) for committee in self.committees
        ]
        local_support_deviation = [
            local / proj if proj != 0 else 0
            for local, proj in zip(local_past_support_projection, past_support_projection)
        ]
        local_support = [s * dev for s, dev in zip(support, local_support_deviation)]
        if constituency.number == 21:  # Zachowujemy wsparcie dla MN w Opolu
            local_support.append(5.37)
        if constituency.number == 32:
            for i, committee in enumerate(self.committees):
                if committee.id == 'nl':
                    cap = 1.8 * support[i]
                    if local_support[i] > cap:
                        local_support[i] = cap
                    break
        return local_support

    def calculate_mandates(self, support, method="dHondt"):
        mandates = [0] * len(self.committees)
        for constituency in self.constituencies:
            local_support = self.calculate_local_support(support, constituency)
            constituency.support = local_support
            constituency.mandates = [0] * len(self.committees)  # Inicjalizacja mandatów dla poszczególnych komitetów
            filtered_local_support = [
                0 if support[i] < self.committees[i].threshold else local_support[i]
                for i in range(len(self.committees))
            ]

            # Wybieramy odpowiednią metodę kalkulacji kwocjentów
            if method == "dHondt":
                quotients = self._calculate_quotients_dhondt(filtered_local_support, constituency.size)
            elif method == "SainteLague":
                quotients = self._calculate_quotients_saintelague(filtered_local_support, constituency.size)
            else:
                raise ValueError("Nieznana metoda: {}".format(method))

            quotients.sort(key=lambda x: x['quotient'], reverse=True)
            top_quotients = quotients[:constituency.size]
            for quotient in top_quotients:
                if quotient['quotient'] > 0:
                    mandates[quotient['committeeIndex']] += 1
                    constituency.mandates[quotient['committeeIndex']] += 1
        return mandates

    def _calculate_quotients_dhondt(self, support, size):
        quotients = []
        for divisor in range(1, size + 1):
            for committee_index in range(len(self.committees)):
                quotient = support[committee_index] / divisor
                quotients.append({'quotient': quotient, 'committeeIndex': committee_index})
        return quotients

    def _calculate_quotients_saintelague(self, support, size):
        quotients = []
        for i in range(1, size + 1):
            divisor = 2 * i - 1  # Dzielniki: 1, 3, 5, ...
            for committee_index in range(len(self.committees)):
                quotient = support[committee_index] / divisor
                quotients.append({'quotient': quotient, 'committeeIndex': committee_index})
        return quotients
