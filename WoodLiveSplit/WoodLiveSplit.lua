local mod = {id='wood-livesplit',name='Wood LiveSplit',version='1.1.1',author='Wood',
 description='Automatic normal Any% timing and splits. Equip Wood-TUNG.lsl in LiveSplit.',tickInterval=1}
local directory = assert(os.getenv('LOCALAPPDATA'),'LOCALAPPDATA is unavailable') .. '/Wood/LiveSplit'
local installed=false
local identity, attempt, elapsed, state = '', 0, 0, 'waiting'
local session=tostring(os.time()) .. ':' .. tostring({})
local events = {-1,-1,-1,-1,-1,-1,-1,-1}
local actors={}
local last_error
local hooks, clicked = {}, {}
local current_api
local publish
local function in_hedge(p)
 return p.Z>=360 and p.Z<=425
end
local function valid(o) return o and o:IsValid() end
local function finite(v) return type(v)=='number' and v==v and v>=0 and v<=86400 end
local function actor(class,world)
 local o=actors[class]
 if valid(o) and o:GetWorld():GetAddress()==world:GetAddress() then return o end
 for _, item in ipairs(FindAllOf(class) or {}) do
  if valid(item) and item:GetWorld():GetAddress()==world:GetAddress() then actors[class]=item; return item end
 end
end
local function event(i,t) if events[i]<0 then events[i]=t end end
local function new_attempt(key,t)
 identity=key; attempt=attempt+1; elapsed=t; actors={}; clicked={}
 events={-1,-1,-1,-1,-1,-1,-1,-1}
 state=t<=2 and 'running' or 'late'
end
local function install_hooks(world,api)
 for _,color in ipairs({'Blue','Green','Red','Yellow'}) do
  local class='BP_' .. color .. 'Valve_C'
  local path='/Game/FPMovement/Blueprints/Items/BP_' .. color .. 'Valve.BP_' .. color .. 'Valve_C:Interact'
  local fn=StaticFindObject(path)
  if valid(fn) and hooks[class]~=fn:GetAddress() then
   local ok,err=pcall(RegisterHook,path,function(context,player_param)
    local callback_ok,callback_error=pcall(function()
     if not current_api or not current_api.get('enabled',true) or state~='running' then return end
     local valve=context:get()
     local player=player_param:get()
     if not valid(valve) or not valid(player) then return end
     local key=tostring(player:GetWorld():GetAddress()) .. ':' .. tostring(player:GetAddress())
     if key~=identity or valve:GetWorld():GetAddress()~=player:GetWorld():GetAddress() or clicked[class] then return end
     local t=tonumber(player.FinalTimerFloat)
     if not finite(t) or t+0.05<elapsed then return end
     clicked[class]=true
     local count=0; for _ in pairs(clicked) do count=count+1 end
     event(count+1,t); elapsed=t
     -- Publish the click timestamp immediately, before the valve animation completes.
     if publish then publish() end
    end)
    if not callback_ok then current_api.log('Valve interaction: ' .. tostring(callback_error)) end
   end)
   if ok then hooks[class]=fn:GetAddress(); api.log('Listening for ' .. color .. ' valve interactions')
   elseif hooks[class..'_error']~=tostring(err) then hooks[class..'_error']=tostring(err);api.log('Could not hook valve interaction: ' .. tostring(err)) end
  end
 end
end
local function read(api)
 local world=api.playerController:GetWorld()
 if not valid(world) then state='waiting'; return end
 if world:GetFName():ToString()~='MAZE' then state='menu'; identity=''; actors={}; return end
 local gs=StaticFindObject('/Script/Engine.Default__GameplayStatics')
 local gi=gs:GetGameInstance(api.playerController)
 if not valid(gi) or gi['Speedrun?']~=true or gi['Checkpoint?']~=false
  or gi['TinyTungSpeedrun?']~=false or gi['B-HOP MODE ON?']~=false then state='unsupported'; identity=''; return end
 local player=gs:GetPlayerPawn(api.playerController,0)
 if not valid(player) or player:GetClass():GetFName():ToString()~='BP_Player_C' then state='waiting'; return end
 local t=tonumber(player.FinalTimerFloat)
 if not finite(t) then error('Game clock unavailable') end
 local key=tostring(world:GetAddress()) .. ':' .. tostring(player:GetAddress())
 if identity~=key or t+0.05<elapsed then new_attempt(key,t) end
 if state=='finished' or state=='late' then return end
 state='running'; elapsed=t
 install_hooks(world,api)
 local objective=actor('BP_TurnValves_C',world)
 if valid(objective) and objective['canStartObjective?']==false then event(1,t) end
 -- The opened door is authoritative; valve animation values can no longer block Hedge.
 local door=actor('BP_ValveDoor_C',world)
 if valid(door) and door['hasOpenedDoorBefore?']==true then event(6,t) end
 if events[6]>=0 and in_hedge(player:K2_GetActorLocation()) then event(7,t) end
 for _,result in ipairs(FindAllOf('WB_EndSpeedrunningTime_C') or {}) do
  if valid(result) and result:IsInViewport() then
   local text=result.TimerNumber:GetText():ToString()
   local minutes,seconds,hundredths=text:match('^(%d+):([0-5]%d)%.(%d%d)$')
   if minutes then
    local finish=tonumber(minutes)*60+tonumber(seconds)+tonumber(hundredths)/100
    if finish<=t+0.1 and finite(finish) then event(8,finish); elapsed=finish; state='finished'; break end
   end
  end
 end
end
local function write(name,content,mode)
 local f,err=io.open(directory .. '/' .. name,mode or 'w')
 if not f then error(err) end
 assert(f:write(content)); f:close()
end
local function install()
 os.execute('cmd /d /c mkdir "' .. directory .. '" >nul 2>nul')
 installed=true
end
function mod.onTick(api)
 current_api=api
 if not installed then install() end
 if not api.get('enabled',true) then state='disabled'
 else
  local ok,err=pcall(read,api)
  if not ok then state='error'; if last_error~=tostring(err) then api.log(tostring(err)); last_error=tostring(err) end
  else last_error=nil end
 end
 publish()
end
publish=function()
 local fields={'WOOD-LIVESPLIT/1',tostring(os.time()),session .. ':' .. tostring(attempt),state,string.format('%.7f',elapsed),'0'}
 for i=1,8 do fields[#fields+1]=string.format('%.7f',events[i]) end
 write('snapshot.txt',table.concat(fields,'|') .. '\n')
end
function mod.buildSettings(api,panel)
 api.label(panel,'WOOD + LIVESPLIT',20)
 api.label(panel,'Install the mod, open LiveSplit, and load Wood-TUNG.lsl. Normal Any% only.',13)
 local status='Waiting for connection'
 if directory then local f=io.open(directory .. '/status.txt','r'); if f then status=f:read('*l') or status; f:close() end end
 api.label(panel,status,13)
 api.toggle(panel,'Automatic timing and splits',api.get('enabled',true),function(v) api.set('enabled',v) end)
 api.label(panel,'Hedge splits at Z 360-425 after the door opens. Finish always ends the run.',12)
end
return mod
