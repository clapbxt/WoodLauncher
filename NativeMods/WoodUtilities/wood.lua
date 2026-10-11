-- All engine operations run on Wood's game-thread dispatcher.
-- Preferences belong to this mod; no vanilla save or OS mouse settings are edited.
local defaults={auto_speedrunner=true,speedrunner_music=true,
    application_volume=1,
    sensitivity_x=1,sensitivity_y=1,invert_x=false,invert_y=false,mouse_smoothing=true}
local settings,game_instance={},nil
local mouse_baselines={}
local original_legacy_scales=nil
local audio_classes={}
local last_error={}
local status={}
local mod={name='Wood Utilities',version='1.0.1',author='Wood',
    description='Automatic speedrunner mode, application volume, and comfortable mouse controls.'}
local function valid(object) return object and object:IsValid() end
local function gs() return StaticFindObject('/Script/Engine.Default__GameplayStatics') end
local function load(api)
    for key,value in pairs(defaults) do
        local fallback=value
        if key=='application_volume' then
            fallback=api.get('mute',false) and 0 or api.get('master_volume',1)
        end
        local stored=api.get(key,fallback)
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
-- Control the final mixer output, including UI and sounds with no class.
-- Keep soundtrack gating separate from the user's one application volume.
local function apply_audio(api,refresh)
    instance(api)
    local master=StaticFindObject('/Engine/EngineSounds/Submixes/MasterSubmixDefault.MasterSubmixDefault')
    assert(valid(master),'Waiting for the application audio output')
    master:SetSubmixOutputVolume(api.playerController,settings.application_volume)
    for _,sound_class in ipairs(FindAllOf('SoundClass') or {}) do
        if valid(sound_class) then
            local short=sound_class:GetFName():ToString():lower()
            if short:find('speedrun',1,true) or short=='majestictung' then
                local name=sound_class:GetFullName()
                local current=sound_class.Properties.Volume
                local state=audio_classes[name]
                if not state or state.object~=sound_class:GetAddress() then
                    state={object=sound_class:GetAddress(),base=current};audio_classes[name]=state
                elseif state.applied and math.abs(current-state.applied)>0.00001 then
                    state.base=current
                end
                state.applied=settings.speedrunner_music and state.base or 0
                sound_class.Properties.Volume=state.applied
            end
        end
    end
end
local function apply_mouse(api)
    local controller=api.playerController
    assert(valid(controller),'Waiting for a player controller')
    local input=StaticFindObject('/Script/Engine.Default__InputSettings')
    assert(valid(input),'Waiting for mouse settings')
    if original_legacy_scales==nil then original_legacy_scales=input.bEnableLegacyInputScales end
    local name=controller:GetFullName()
    local state=mouse_baselines[name]
    if not state or state.object~=controller:GetAddress() then
        -- With legacy scales disabled, Unreal's effective multiplier is 1,
        -- even though the unused deprecated properties contain other values.
        state={object=controller:GetAddress(),
            x=original_legacy_scales and controller.InputYawScale or 1,
            y=original_legacy_scales and controller.InputPitchScale or 1}
        mouse_baselines[name]=state
    end
    input.bEnableLegacyInputScales=true
    controller:SetDeprecatedInputYawScale(state.x*settings.sensitivity_x*(settings.invert_x and -1 or 1))
    controller:SetDeprecatedInputPitchScale(state.y*settings.sensitivity_y*(settings.invert_y and -1 or 1))
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
        elseif key=='application_volume' then
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
    local audio=api.section(panel,'AUDIO','One volume control for TUNG, including the title screen, menus, music, and effects. 0% mutes the application.')
    local percent=function(value) return string.format('%d%%',math.floor(value*100+0.5)) end
    slider(audio,'Application volume','application_volume',0,1,0.01,percent)
    api.button(audio,'Reset audio',function() reset({'application_volume'}) end)
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
