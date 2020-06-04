from saleae.analyzers import *

class Transaction:
    def __init__(self, start_time):
        self.start_time = start_time
        self.end_time = None
        self.data = bytearray()
        self.is_multibyte_read = False
        self.is_read = False
        self.address = -1


class i2cAnalyzer(HighLevelAnalyzer):
    def __init__(self):
        self.current_i2c_transaction = None

    def on_transaction(self, transaction: Transaction):
        raise RuntimeError('Must implement on_transaction')

    def decode(self, frame: AnalyzerFrame):
        if frame.type == 'start':
            self.current_i2c_transaction = Transaction(frame.start_time)
        elif frame.type == 'stop' and self.current_i2c_transaction:
            self.current_i2c_transaction.end_time = frame.end_time

            if self.current_i2c_transaction:
                ret_frames = self.on_transaction(self.current_i2c_transaction)
                self.current_i2c_transaction = None

                return ret_frames

        if self.current_i2c_transaction is not None:
            if frame.type == 'address':
                address = frame.data['address'][0]
                self.current_i2c_transaction.address = address
                self.current_i2c_transaction.is_read = frame.data['read']
            elif frame.type == 'data':
                byte = frame.data['data'][0]
                self.current_i2c_transaction.data.append(byte)
