# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

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
