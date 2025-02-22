import re
from PySide6.QtGui import QValidator

class DotCommaDoubleValidator(QValidator):
    def __init__(self, bottom, top, decimals, parent=None):
        super().__init__(parent)
        self.bottom = bottom
        self.top = top
        self.decimals = decimals
        self.regex = re.compile(r'^\d+([.,]\d{0,' + str(decimals) + '})?$')

    def validate(self, input_str, pos):
        if input_str == "":
            return (QValidator.Intermediate, input_str, pos)
        if not self.regex.match(input_str):
            return (QValidator.Invalid, input_str, pos)
        normalized = input_str.replace(',', '.')
        try:
            value = float(normalized)
        except ValueError:
            return (QValidator.Invalid, input_str, pos)
        if self.bottom <= value <= self.top:
            return (QValidator.Acceptable, input_str, pos)
        else:
            return (QValidator.Invalid, input_str, pos)

    def fixup(self, input_str):
        return input_str.replace(',', '.')
