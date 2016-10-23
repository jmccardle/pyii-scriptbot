class ReadForwardFile:
    def __init__(self, filename):
        self.filename = filename
        try:
            with open(self.filename, "r") as f:
                f.seek(0,2) #go to end of the file
                self.position = f.tell()
        except IOError: #file not found, probably.
            #Since I only read lines from files due to inotify events, this is only
            #an issue on first startups when the files don't exist yet.
            self.position = 0
        self.text = ''

    def complete_lines(self):
        with open(self.filename, "r") as f:
            f.seek(self.position)
            self.text += f.read()
            self.position = f.tell()
        lines = self.text.split('\n')[0:-1]
        self.text = self.text.split('\n')[-1]
        return lines
