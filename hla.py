# High Level Analyzer
# For more information and documentation, please go to https://github.com/saleae/logic2-examples

from saleae.analyzers import *
from i2c_analyzer import i2cAnalyzer, Transaction


class JoyFeatherWingAnalyzer(i2cAnalyzer):
    result_types = {
        'buttons': {'format': 'a: {{data.a}}, b: {{data.b}}, x: {{data.x}}, y: {{data.y}}, sel: {{data.sel}}'},
        'joystick': {'format': 'axis: {{data.axis}}, value: {{data.value}}'},
        'error': {'format': 'reason: {{data.reason}}, base_address: {{data.base_address}}, function_address: {{data.function_address}}'}
    }

    def __init__(self):
        super().__init__()
        self.current_transaction = None

    def on_transaction(self, tx: Transaction):
        if tx.address != 73:
            return

        if tx.is_read:
            if self.current_transaction is None:
                return

            register = self.current_transaction.data
            base_address = register[0]
            function_address = register[1]

            extra_data = {}
            frame = None
            if base_address == 1 and function_address == 4:  # GPIO
                gpio_register = tx.data[0]
                gpio_register = (gpio_register << 8) + tx.data[1]
                gpio_register = (gpio_register << 8) + tx.data[2]
                gpio_register = (gpio_register << 8) + tx.data[3]
                extra_data['a'] = not bool(gpio_register & (1 << 6))
                extra_data['b'] = not bool(gpio_register & (1 << 7))
                extra_data['x'] = not bool(gpio_register & (1 << 10))
                extra_data['y'] = not bool(gpio_register & (1 << 9))
                extra_data['sel'] = not bool(gpio_register & (1 << 14))

                frame = AnalyzerFrame('buttons', self.current_transaction.start_time, tx.end_time,
                                      dict(base_address=base_address,
                                      function_address=function_address, **extra_data))

            elif base_address == 9 and function_address in (7, 8):
                # 0 - 1023
                value = (tx.data[0] << 8) + tx.data[1]
                # Shift around 0
                value = value - 512
                value = float(value) / 512.0
                axis = 'X' if function_address == 8 else 'Y'
                frame = AnalyzerFrame('joystick', self.current_transaction.start_time, tx.end_time,
                                      dict(axis=axis, value=value))

            else:
                frame = AnalyzerFrame('error', self.current_transaction.start_time, tx.end_time,
                                      dict(reason='unrecognized addresses',
                                      base_address=base_address,
                                      function_address=function_address, **extra_data))

            self.current_transaction = None
            return frame

        else:
            if self.current_transaction is not None:
                frame = AnalyzerFrame('error', self.current_transaction.start_time,
                                      self.current_transaction.end_time, dict(reason='expected read after write'))
                self.current_transaction = None
                return frame

            if len(tx.data) != 2:
                # Unexpected
                return AnalyzerFrame('error', tx.start_time, tx.end_time, dict(reason='expected 2 register bytes'))

            self.current_transaction = tx
