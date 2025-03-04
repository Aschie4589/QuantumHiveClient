class Line:
    def __init__(self, width, text):
        self.width = width
        self.text = text

    def __str__(self):
        if len(self.text) < self.width:
            return self.text + " "*(self.width-len(self.text))
        elif len(self.text) >= self.width:
            return self.text[:self.width]

    def resize(self, new_width):
        self.width = new_width
        # pad with spaces if necessary
        if len(self.text) < self.width:
            self.text += " "*(self.width-len(self.text))


    def write_text(self, text, position=0):
        if position + len(text) < self.width:
            self.text = self.text[:position] + text + self.text[position+len(text):]
        elif position < self.width:
            self.text = self.text[:position] + text
        
