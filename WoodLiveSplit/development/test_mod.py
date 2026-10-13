from pathlib import Path
from lupa import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
files={}; io.open=function(path,mode)
 if mode=='r' then return nil end
 return {write=function(self,text) files[path]=text;return self end,close=function() end}
end
os.execute=function() return true end
os.getenv=function() return 'C:/Test' end
world={GetAddress=function() return 10 end,GetFName=function() return {ToString=function() return map end} end,IsValid=function() return true end}
map='MAZE'
function object(class)
 local o={IsValid=function() return true end,GetWorld=function() return world end}
 o.GetClass=function() return {GetFName=function() return {ToString=function() return class end} end,
  ForEachProperty=function(self,callback) callback({GetFName=function()return {ToString=function()return 'RotateValveTimeline_RotateValveTrack_TEST'end}end}) end} end
 return o
end
gi={['Speedrun?']=true,['Checkpoint?']=false,['TinyTungSpeedrun?']=false,['B-HOP MODE ON?']=false,IsValid=function()return true end}
player=object('BP_Player_C');player.FinalTimerFloat=0.1;player.GetAddress=function()return 20 end
grounded=true;position={X=0,Y=0,Z=0}
player.CharacterMovement={IsMovingOnGround=function()return grounded end}
player.K2_GetActorLocation=function()return position end
actors={};for _,class in ipairs({'BP_BlueValve_C','BP_GreenValve_C','BP_RedValve_C','BP_YellowValve_C','BP_TurnValves_C','BP_ValveDoor_C'})do actors[class]=object(class) end
actors.BP_TurnValves_C['canStartObjective?']=true
actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=false
results={}
FindAllOf=function(class)if class=='WB_EndSpeedrunningTime_C'then return results end;return {actors[class]} end
hooks={}
RegisterHook=function(path,callback)hooks[path]=callback;return 1,2 end
StaticFindObject=function(path)
 if path:match(':Interact$')then return {IsValid=function()return true end,GetAddress=function()return 100 end}end
 return {GetGameInstance=function()return gi end,GetPlayerPawn=function()return player end}
end
api={playerController={GetWorld=function()return world end},get=function(k,v)return enabled~=false end,log=function(message)end}
''')
mod = lua.execute(Path(__file__).with_name('mod.lua').read_text())
def tick():
    mod.onTick(lua.globals().api)
    frame = lua.globals().files['C:/Test/Wood/LiveSplit/snapshot.txt'].strip().split('|')
    assert len(frame) == 14
    return frame
assert tick()[3] == 'running'
lua.execute("player.FinalTimerFloat=2;actors.BP_TurnValves_C['canStartObjective?']=false")
assert float(tick()[6]) == 2
for i, name in enumerate(('Blue','Green','Red','Yellow'), 1):
    lua.execute(f"""
player.FinalTimerFloat={i+2}
local path='/Game/FPMovement/Blueprints/Items/BP_{name}Valve.BP_{name}Valve_C:Interact'
local context={{get=function()return actors.BP_{name}Valve_C end}}
local param={{get=function()return player end}}
hooks[path](context,param)
hooks[path](context,param)
""")
    # A click publishes immediately with the animation track still at zero/unset.
    frame = lua.globals().files['C:/Test/Wood/LiveSplit/snapshot.txt'].strip().split('|')
    assert float(frame[6+i]) == i+2
    assert float(tick()[6+i]) == i+2
    lua.execute(f'actors.BP_{name}Valve_C.RotateValveTimeline_RotateValveTrack_TEST=360')
lua.execute("player.FinalTimerFloat=7;actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=true;grounded=false")
assert float(tick()[11]) == 7
lua.execute('player.FinalTimerFloat=8;grounded=true;position={X=700,Y=2050,Z=400}')
assert float(tick()[12]) == 8
lua.execute("player.FinalTimerFloat=9.8;results={{IsValid=function()return true end,IsInViewport=function()return true end,TimerNumber={GetText=function()return {ToString=function()return '00:09.23'end}end}}}")
assert tick()[3] == 'finished'
assert float(tick()[13]) == 9.23
lua.execute('player.FinalTimerFloat=10')
assert float(tick()[4]) == 9.23
lua.execute("map='L_Demo'")
assert tick()[3] == 'menu'
lua.execute("map='MAZE';player.FinalTimerFloat=0.1;results={};actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=false;position={X=0,Y=0,Z=0}")
assert tick()[3] == 'running'
lua.execute("actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=false;position={X=0,Y=0,Z=0}")
tick()
# Height-only detection ignores horizontal position and grounded/airborne state.
lua.execute("actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=false;position={X=-5000,Y=9000,Z=400};grounded=false")
assert float(tick()[12]) == -1
lua.execute("actors.BP_ValveDoor_C['hasOpenedDoorBefore?']=true;player.FinalTimerFloat=3;position.Z=426")
assert float(tick()[12]) == -1
lua.execute('position.Z=359')
assert float(tick()[12]) == -1
lua.execute('player.FinalTimerFloat=4;position.Z=360')
assert float(tick()[12]) == 4
lua.execute('player.FinalTimerFloat=5;position.Z=425')
assert float(tick()[12]) == 4
lua.execute("gi['TinyTungSpeedrun?']=true")
assert tick()[3] == 'unsupported'
lua.execute("gi['TinyTungSpeedrun?']=false;player.FinalTimerFloat=30")
assert tick()[3] == 'late'
lua.execute('enabled=false')
assert tick()[3] == 'disabled'
print('Mod event tests passed')
