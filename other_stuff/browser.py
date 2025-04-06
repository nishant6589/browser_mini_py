# Explore and learn the browser development
import socket
import ssl 
import tkinter
import tkinter.font


class URL:
    def __init__(self, url):
        #splitting http and url
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        if self.scheme == "http":
            self.port = 80 
        elif self.scheme == "https":
            self.port = 443 

        #identifing the host and the url
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)

        #adding support for port in link
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        self.path = "/" + url 

        

    def request(self):
        #definging the socket connection
        s = socket.socket(
            family= socket.AF_INET,
            type= socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        #connecting to the host
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname= self.host)

        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n"
        s.send(request.encode("utf8"))

        #to read the response 
        response = s.makefile("r", encoding = "utf8",  newline = "\r\n")

        #converting response into a meaning 
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        print(version, status, explanation)

        #header here
        response_header = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break 
            header, value = line.split(":", 1)
            response_header[header.casefold()] = value.strip()
        # print(response_header)
        assert "transfer-encoding" not in response_header
        assert "content-encoding" not in response_header

        content = response.read()
        s.close()

        return content
    

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP , VSTEP = 15, 18

class Layout:
    def __init__(self, tokens):
        self.tokens = tokens
        self.display_list = []
        self.line = []
        self.weight = "normal"
        self.style = "roman"
        self.cursor_x = HSTEP
        self.cursor_y =  VSTEP
        self.size = 12
        

        for tok in tokens:
            self.token(tok)
        self.flush()
    
    def token(self, tok):
        if isinstance(tok, Text):
            for wor in tok.text.split():
                self.word(wor)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP
        
    def word(self, wor):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(wor)
        if self.cursor_x+w > WIDTH - HSTEP:
            self.flush()
            
        
        self.line.append((self.cursor_x, wor, font))
        self.cursor_x += w + font.measure(" ")

        
    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []

FONTS = {}
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

class Text:
    def __init__(self, text, parent):
        self.text = text 
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)



class Element:
    def __init__(self, tag, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return f"<{self.tag}>"
    

class HTMLParser:
    def __init__(self, body):
        self.body = body 
        self.unfinished = []

    def parse(self):
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer: self.add_text(buffer)
                buffer = ""
            elif c == ">":
                in_tag = False 
                self.add_tag(buffer)
                buffer = ""
            else:
                buffer += c 
        if not in_tag and buffer:
            self.add_text(buffer)
        return self.finish()
    
    def add_text(self, text):
        if text.isspace(): return
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        if tag.startswith("!"): return
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return 
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node) 
        else:
            parent = self.unfinished[-1] if self.unfinished else None 
            node = Element(tag, parent)
            self.unfinished.append(node)
    
    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
        


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width= WIDTH,
            height = HEIGHT,
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)


    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()


    def draw(self):
        self.canvas.delete("all")
        for x, y, e, f in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y +  f.metrics("linespace") < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text = e, font= f, anchor="nw")


    def load(self, url):
        body = url.request()
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)          


if __name__ == "__main__":
    import sys 
    # Browser().load(URL(sys.argv[1]))
    # tkinter.mainloop()
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)