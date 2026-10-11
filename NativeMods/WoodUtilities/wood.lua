-- All engine operations run on Wood's game-thread dispatcher.
-- Preferences belong to this mod; no vanilla save or OS mouse settings are edited.
local defaults={auto_speedrunner=true,speedrunner_music=true,
    master_volume=1,music_volume=1,effects_volume=1,voice_volume=1,mute=false,
    sensitivity_x=1,sensitivity_y=1,invert_x=false,invert_y=false,mouse_smoothing=true}
local settings,controller,game_instance,hooks={},nil,nil,{}
local audio_classes={}
local last_error={}
local status={}
local mod={name='Wood Utilities',version='1.0.0',author='Wood',
    description='Automatic speedrunner mode, audio levels, and comfortable mouse controls.'}
local function valid(object) return object and object:IsValid() end
local function gs() return StaticFindObject('/Script/Engine.Default__GameplayStatics') end
local function load(api)
    for key,value in pairs(defaults) do
        local stored=api.get(key,value)
        if type(value)=='number' then
            local high=key:find('sensitivity',1,true) and 3 or 1
            local low=key:find('sensitivity',1,true) and 0.1 or 0
            if type(stored)~='number' or stored~=stored then stored=value end
            stored=math.max(low,math.min(high,stored))
        end
        settings[key]=stored
    end
end
local function attempt(api,key,callback)
    local ok,err=pcall(callback)
    if not ok then status[key]='Unavailable: '..tostring(err)
    elseif key~='speedrunner' then status[key]='Applied' end
    if not ok and last_error[key]~=tostring(err) then api.log(key..': '..tostring(err)) end
    last_error[key]=not ok and tostring(err) or nil
    return ok
end
local function instance(api)
    assert(valid(api.playerController),'Waiting for a player controller')
    local current=gs():GetGameInstance(api.playerController)
    assert(valid(current),'Waiting for TUNG game settings')
    return current
end
local function apply_speedrunner(api,force)
    local current=instance(api)
    if current:GetFullName()~=game_instance then
        game_instance=current:GetFullName()
        if settings.auto_speedrunner then force=true end
    end
    if force and settings.auto_speedrunner then
        current['Speedrun?']=true
        current['SpeedrunMusic?']=settings.speedrunner_music
        current:SpeedrunModeOn()
    end
    -- Music follows the preference only while speedrunner mode is active.
    if current['Speedrun?'] then
        current['SpeedrunMusic?']=settings.speedrunner_music
        for _,widget in ipairs(FindAllOf('WB_TUNG_SETTINGS3_C') or {}) do
            if valid(widget) and valid(widget.Music) and widget.Music:IsChecked()~=settings.speedrunner_music then
                widget.Music:SetIsChecked(settings.speedrunner_music)
                widget:BndEvt__WB_TUNG_SETTINGS3_music_K2Node_ComponentBoundEvent_1_OnCheckBoxComponentStateChanged__DelegateSignature(settings.speedrunner_music)
            end
        end
    end
    status.speedrunner=current['Speedrun?'] and 'Speedrunner mode enabled' or 'Speedrunner mode off'
end
-- TUNG uses several independent roots, and its title MetaSound has no class.
-- Write the existing reflected volume field in place: no temporary SoundMix can
-- be collected or disappear when the game changes its own active mix.
local function category(sound_class)
    local name=sound_class:GetFName():ToString():lower()
    if name:find('music',1,true) or name:find('speedrun',1,true) or name=='majestictung' then return 'music_volume' end
    if name:find('voice',1,true) then return 'voice_volume' end
    if name=='master' then return nil end
    return 'effects_volume'
end
local music_assets={OneTung=true,MS_OneTung=true,
    ['tension-in-the-dark-SBA-346822581']=true,['tension-builder-2-SBA-300286335']=true,
    ['unforgiven-SBA-347637026']=true,DuBistGutGenugSlowed3DAudio=true}
local function route_audio()
    local music=StaticFindObject('/Engine/EngineSounds/Music.Music')
    local effects=StaticFindObject('/Engine/EngineSounds/SFX.SFX')
    local voice=StaticFindObject('/Engine/EngineSounds/Voice.Voice')
    for _,kind in ipairs({'SoundWave','SoundCue','MetaSoundSource'}) do
        for _,sound in ipairs(FindAllOf(kind) or {}) do
            if valid(sound) then
                local path=sound:GetFullName()
                if not path:find('Default__',1,true) then
                    local assigned=sound.SoundClassObject
                    if path:find('/Speech/',1,true) and valid(voice) then
                        sound.SoundClassObject=voice
                    elseif music_assets[sound:GetFName():ToString()] and valid(music) then
                        sound.SoundClassObject=music
                    elseif valid(assigned) and assigned:GetFName():ToString()=='Master' and valid(effects) then
                        -- Vanilla footsteps use Master directly, bypassing SFX.
                        sound.SoundClassObject=effects
                    elseif not valid(assigned) and valid(effects) then
                        sound.SoundClassObject=effects
                    end
                end
            end
        end
    end
end
local function apply_audio(api,refresh)
    instance(api)
    route_audio()
    local count=0
    for _,sound_class in ipairs(FindAllOf('SoundClass') or {}) do
        if valid(sound_class) then
            local name=sound_class:GetFullName()
            if not name:find('Default__',1,true) then
                count=count+1
                local current=sound_class.Properties.Volume
                local state=audio_classes[name]
                if not state or state.object~=sound_class:GetAddress() then
                    state={object=sound_class:GetAddress(),base=current};audio_classes[name]=state
                elseif state.applied and math.abs(current-state.applied)>0.00001 then
                    -- Keep vanilla changes (such as muting a soundtrack) as the
                    -- baseline instead of multiplying our last gain repeatedly.
                    state.base=current
                end
                local parent=sound_class.ParentClass
                local own_category=category(sound_class)
                local gain=1
                if not valid(parent) then
                    gain=settings.mute and 0 or settings.master_volume
                    if own_category then gain=gain*settings[own_category] end
                elseif own_category and category(parent)~=own_category then
                    gain=settings[own_category]
                end
                local short=sound_class:GetFName():ToString():lower()
                if not settings.speedrunner_music and (short:find('speedrun',1,true) or short=='majestictung') then gain=0 end
                state.applied=state.base*gain
                sound_class.Properties.Volume=state.applied
            end
        end
    end
    assert(count>0,'Waiting for sound classes')
end
local function apply_mouse(api)
    controller=api.playerController
    local function register(path,axis,is_pawn)
        if hooks[path] then return end
        local first,second=RegisterHook(path,function(context,value)
            local object=context:get()
            if not valid(object) or not valid(controller) then return end
            local owner=is_pawn and object.Controller or object
            if not valid(owner) or owner:GetFullName()~=controller:GetFullName() then return end
            local gain=settings['sensitivity_'..axis]*(settings['invert_'..axis] and -1 or 1)
            value:set(value:get()*gain)
        end)
        hooks[path]={first,second}
    end
    register('/Script/Engine.Pawn:AddControllerYawInput','x',true)
    register('/Script/Engine.Pawn:AddControllerPitchInput','y',true)
    register('/Script/Engine.PlayerController:AddYawInput','x',false)
    register('/Script/Engine.PlayerController:AddPitchInput','y',false)
    local input=StaticFindObject('/Script/Engine.Default__InputSettings')
    assert(valid(input),'Waiting for mouse settings')
    input.bEnableMouseSmoothing=settings.mouse_smoothing
end
local function apply(api,force)
    attempt(api,'speedrunner',function() apply_speedrunner(api,force) end)
    attempt(api,'audio',function() apply_audio(api,true) end)
    attempt(api,'mouse',function() apply_mouse(api) end)
end
function mod.onWorldReady(api)
    load(api)
    apply(api,true)
end
function mod.onTick(api)
    if settings.auto_speedrunner==nil then load(api) end
    attempt(api,'speedrunner',function() apply_speedrunner(api,false) end)
    attempt(api,'audio',function() apply_audio(api,false) end)
    if last_error.mouse then attempt(api,'mouse',function() apply_mouse(api) end) end
end
function mod.buildSettings(api,panel)
    load(api)
    local function change(key,value)
        settings[key]=value;api.set(key,value)
        if key=='auto_speedrunner' or key=='speedrunner_music' then
            attempt(api,'speedrunner',function() apply_speedrunner(api,key=='auto_speedrunner' and value) end)
            if key=='speedrunner_music' then attempt(api,'audio',function() apply_audio(api,true) end) end
        elseif key:find('volume',1,true) or key=='mute' then
            attempt(api,'audio',function() apply_audio(api,true) end)
        else attempt(api,'mouse',function() apply_mouse(api) end) end
    end
    local function toggle(parent,label,key)
        return api.toggle(parent,label,settings[key],function(value) change(key,value) end)
    end
    local function slider(parent,label,key,low,high,step,format)
        return api.slider(parent,label,low,high,step,settings[key],function(value) change(key,value) end,format)
    end
    local function reset(keys)
        for _,key in ipairs(keys) do settings[key]=defaults[key];api.set(key,defaults[key]) end
        apply(api,false);api.refreshSettings()
    end
    local runner=api.section(panel,'SPEEDRUNNER','Use TUNG\'s native mode automatically. Disabling auto mode leaves your current run unchanged. Soundtrack selection applies on your next run; turning music off also mutes it now.')
    toggle(runner,'Auto-speedrunner mode','auto_speedrunner')
    toggle(runner,'Speedrunner music','speedrunner_music')
    api.label(runner,status.speedrunner or 'Applies when the game starts',13)
    local audio=api.section(panel,'AUDIO','Levels apply immediately. Music includes the speedrunner soundtrack.')
    local percent=function(value) return string.format('%d%%',math.floor(value*100+0.5)) end
    slider(audio,'Master volume','master_volume',0,1,0.01,percent)
    slider(audio,'Music volume','music_volume',0,1,0.01,percent)
    slider(audio,'Effects volume','effects_volume',0,1,0.01,percent)
    slider(audio,'Voice volume','voice_volume',0,1,0.01,percent)
    toggle(audio,'Mute all audio','mute')
    api.button(audio,'Reset audio',function() reset({'master_volume','music_volume','effects_volume','voice_volume','mute'}) end)
    if last_error.audio then api.label(audio,status.audio,13) end
    local mouse=api.section(panel,'MOUSE','Sensitivity is relative to TUNG\'s normal look speed: 1.00x keeps the default.')
    local multiplier=function(value) return string.format('%.2fx',value) end
    slider(mouse,'Horizontal sensitivity','sensitivity_x',0.1,3,0.05,multiplier)
    slider(mouse,'Vertical sensitivity','sensitivity_y',0.1,3,0.05,multiplier)
    toggle(mouse,'Invert horizontal look','invert_x')
    toggle(mouse,'Invert vertical look','invert_y')
    toggle(mouse,'Mouse smoothing','mouse_smoothing')
    api.button(mouse,'Reset mouse',function() reset({'sensitivity_x','sensitivity_y','invert_x','invert_y','mouse_smoothing'}) end)
    if last_error.mouse then api.label(mouse,status.mouse,13) end
    api.label(panel,'Changes save automatically. Disable Wood Utilities in the launcher and restart to return to vanilla controls.',13)
end
return mod
