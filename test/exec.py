from moat.logging import log, TRACE,ERROR

def running(event):
    log(TRACE,"PY Event called",event)

def not_running(event):
    log(ERROR,"PY bad event called",event)
    
def called(env,*a,**k):
    log(TRACE,"PY Proc called",env,a,k)
    env.on("test","me", doc="Test me harder",name="foo test bar")(running)
    env.on("test","me","not", doc="dummy")(not_running)
    log(TRACE,"PY Proc done")
