state = []
email = ""
admin = ""
builder_list = ""

def push(s):
  state.append(s)

def pop():
  state.pop()

def get():
  return "%s" % state
