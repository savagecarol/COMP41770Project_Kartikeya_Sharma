class Transaction:
    def __init__(self, sender, receiver, transaction_fees, amount):
        self.__sender = sender
        self.__receiver = receiver
        self.__transaction_fees = transaction_fees
        self.__amount = amount

    @property
    def sender(self):
        return self.__sender

    @sender.setter
    def sender(self, value):
        self.__sender = value

    @property
    def receiver(self):
        return self.__receiver

    @receiver.setter
    def receiver(self, value):
        self.__receiver = value


    @property
    def transaction_fees(self):
        return self.__transaction_fees

    @transaction_fees.setter
    def transaction_fees(self, value):
        self.__transaction_fees = value

    @property
    def amount(self):
        return self.__amount

    @amount.setter
    def amount(self, value):
        self.__amount = value

    def tx_to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "transaction_fees": self.transaction_fees,
            "amount": self.amount
        }

    @staticmethod
    def from_dict(data):
        return Transaction(
            data["sender"],
            data["receiver"],
            data["transaction_fees"],
            data["amount"]
        )