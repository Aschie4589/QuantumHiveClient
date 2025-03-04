from src.line import Line

class Canvas:
    def __init__(self, max_width, max_height):
        self.max_width = max_width
        self.max_height = max_height
        self.width = 0
        self.height = 0
        self.lines = []

        self.scrolling = False

    def from_list(self, str_list):
        # never allow more lines than max_height

        self.width = max([len(line) for line in str_list]) if self.width == 0 else self.width
        self.lines = [Line(self.width, line) for line in str_list[:self.max_height]]
        self.height = len(self.lines)

    def resize(self):
        # find new width and height
        new_width = max([len(line.text) for line in self.lines]) if self.lines else 0
        new_width = min(new_width, self.max_width)
        new_height = len(self.lines)
        # resize all lines
        for line in self.lines:
            line.resize(new_width)
        self.width = new_width
        self.height = new_height

    def __str__(self):
        return "\n".join([str(line) for line in self.lines])

    def write_line(self, text, x, y):
        if y < self.height:
            self.lines[y].write_text(text, x)

    def add_line(self, text):
        if self.height < self.max_height:
            # if text is longer than width, extend the canvas
            if len(text) > self.width:
                self.width = len(text)
            # add line
            self.lines.append(Line(self.width, text))
        self.resize() 

    def replace(self, new_canvas, x, y):
        # replace lines from y to y+new_canvas.height-1
        for i, line in enumerate(new_canvas.lines):
            if y+i < self.height:
                # Write text
                self.lines[y+i].write_text(str(line), x)
    
    def to_list(self):
        return [str(line) for line in self.lines]
    
    def add_border(self, extend = False):
        '''Add a border around the canvas'''
        if not extend:
            for i, line in enumerate(self.lines):
                if i == 0 or i == self.height-1:
                    self.lines[i].write_text("-"*self.width)
                else:
                    self.lines[i].write_text("|"+line.text+"|")
        else:            
            # add side borders
            for i, line in enumerate(self.lines):
                self.lines[i].write_text("|"+line.text+"|")
            self.resize()
            # add top and bottom border
            self.add_line("-"*self.width)
            self.add_line("-"*self.width)
            # next shuffle lines around so the border is also at the top
            self.lines = [self.lines[-1]] + self.lines[:-1]
        self.resize()

