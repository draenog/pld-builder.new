state = []

def push(s):
  state.append(s)

def pop():
  state.pop()

def get():
  return "%s" % state
