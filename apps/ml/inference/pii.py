"""Request-scoped direct identifier protection for explicitly consented hosted calls."""
import re
import secrets


class PiiVault:
    def __init__(self):
        self.prefix='PRIVATE_'+secrets.token_hex(6).upper()
        self.values={}
        self.reverse={}

    def protect(self,text):
        patterns=[r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
                  r'(?<!\w)(?:\+91[- ]?)?[6-9]\d{9}(?!\w)',
                  r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
                  r'(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?!\d)']
        def replace(match):
            value=match.group()
            if value not in self.reverse:
                token=f'{self.prefix}_{len(self.values)+1}'
                self.values[token]=value;self.reverse[value]=token
            return self.reverse[value]
        for pattern in patterns:text=re.sub(pattern,replace,text)
        return text

    def restore(self,text):
        pattern=r'\b'+re.escape(self.prefix)+r'_\d+\b'
        return re.sub(pattern,lambda match:self.values.get(match.group(),match.group()),text)
