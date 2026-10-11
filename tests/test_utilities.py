"""Exercise Utilities through the actual native menu, lifecycle, and saved settings."""
from pathlib import Path
import tempfile
import unittest
from lupa.lua54 import LuaRuntime
from test_mod_library import BOOT

ENGINE = r'''
local original_object=object
function object(class)
 local o=original_object(class)
 function o:IsValid() return not self.invalid end
 function o:SetToolTipText(value) self.tooltip=value:ToString() end
 function o:GetFName() return FText(self.name or self.class) end
 function o:GetAddress() return tostring(self) end
 return o
end
invalid={IsValid=function() return false end}
gi=object('GI');gi['Speedrun?']=false;gi['SpeedrunMusic?']=true;runner_calls=0
function gi:GetFullName() return 'GameInstance' end
function gi:SpeedrunModeOn() runner_calls=runner_calls+1;self['Speedrun?']=true end
input_settings=object('InputSettings');input_settings.bEnableMouseSmoothing=true
classes={}; overrides={}; push_count=0;registered={};hook_count=0;override_count=0
function sound_class(name,parent,volume)
 local sc=object('SoundClass');sc.name=name;sc.ParentClass=parent or invalid;sc.Properties={Volume=volume or 1}
 function sc:GetFullName() return 'SoundClass /Game/'..self.name end
 table.insert(classes,sc);return sc
end
master=sound_class('Master');music_class=sound_class('Music',master)
fx=sound_class('SFX',master);attack=sound_class('Normal_Attack',fx)
voice=sound_class('Voice',master);speedrun=sound_class('Speedrun',nil,0)
never_mute=sound_class('NeverMute');dream=sound_class('DreamSpeedrunMusic')
gameplay=object('GameplayStatics')
function gameplay:GetGameInstance() return gi end
function gameplay:SetSoundMixClassOverride(pc,mix,sc,gain,pitch,fade,children)
 assert(pitch==1 and fade==0 and children==false)
 overrides[sc.name]=gain;override_count=override_count+1
end
function gameplay:PushSoundMixModifier() push_count=push_count+1 end
function gameplay:PopSoundMixModifier() end
local original_find=StaticFindObject
function StaticFindObject(path)
 if path=='/Script/Engine.Default__GameplayStatics' then return gameplay end
 if path=='/Script/Engine.Default__InputSettings' then return input_settings end
 return original_find(path)
end
assets={}
function asset(path,sc)
 local o=object('SoundWave');o.SoundClassObject=sc or invalid
 function o:GetFullName() return path end
 function o:GetFName() return FText(path:match('%.([^%.]+)$') or path) end
 table.insert(assets,o);return o
end
speech=asset('SoundWave /Game/SYSTEM/Sounds/Speech/TTS/Hello.Hello',never_mute)
footstep=asset('SoundWave /Game/Footstep',master)
title=asset('MetaSoundSource /Game/SYSTEM/Sounds/MS_OneTung.MS_OneTung')
widget=object('WB_TUNG_SETTINGS3_C');widget.Music=object('CheckBox');widget.Music.checked=true
function widget.Music:IsChecked() return self.checked end
function widget.Music:SetIsChecked(value) self.checked=value end
music_events=0
function widget:BndEvt__WB_TUNG_SETTINGS3_music_K2Node_ComponentBoundEvent_1_OnCheckBoxComponentStateChanged__DelegateSignature(value) music_events=music_events+1 end
local base_find=StaticFindObject
function StaticFindObject(path)
 if path=='/Engine/EngineSounds/Music.Music' then return music_class end
 if path=='/Engine/EngineSounds/SFX.SFX' then return fx end
 if path=='/Engine/EngineSounds/Voice.Voice' then return voice end
 return base_find(path)
end
function FindAllOf(class)
 if class=='SoundClass' then return classes end
 if class=='SoundWave' then return {speech,footstep} end
 if class=='MetaSoundSource' then return {title} end
 if class=='WB_TUNG_SETTINGS3_C' then return {widget} end
 return {}
end
setmetatable(overrides,{__index=function(t,key) for _,c in ipairs(classes) do if c.name==key then return c.Properties.Volume end end end})
local original_construct=StaticConstructObject
function StaticConstructObject(class,...)
 local result=original_construct(class,...)
 if class.class=='/Script/Engine.SoundMix' then last_mix=result end
 return result
end
function RegisterHook(path,fn)
 assert(not registered[path],'Duplicate input hook')
 registered[path]=fn;hook_count=hook_count+1;return hook_count,hook_count+100
end
function input_value(path,owner,initial)
 local value=initial
 registered[path]({get=function() return owner end},{get=function() return value end,set=function(self,new) value=new end})
 return value
end
function control(label)
 for _,action in ipairs(test_ui.actions.details) do if action.widget.tooltip==label then return action.widget end end
 for _,entry in ipairs(test_ui.controls) do if entry.widget.tooltip==label then return entry.widget end end
 error('Missing native control '..label)
end
function slider_value(label,value) control(label):SetValue(value);tick() end
'''


class UtilitiesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wood-utilities-')
        self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name)/'.wood'
        self.data.mkdir()
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().test_root=self.temp.name.replace('\\','/')
        self.lua.globals().test_menu=Path('NativeMods/WoodRuntime/Scripts/menu.lua').resolve().as_posix()
        self.lua.globals().test_utilities=Path('NativeMods/WoodUtilities/wood.lua').resolve().as_posix()
        boot=BOOT.replace("if path:find('extensions.lua',1,true) then return {",
                          "if path:find('extensions.lua',1,true) then return {\n {id='WoodUtilities',path=test_utilities,name='Wood Utilities',enabled=true},")
        self.lua.execute(boot+ENGINE)
        self.lua.execute("assert(load(...,'@NativeMods/WoodRuntime/Scripts/main.lua'))()",Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8'))
        self.lua.execute("tick();keys.F10();assert(click('Wood Utilities'))")

    def tearDown(self):
        self.lua.execute('assert(unsafe_style_calls==0)')

    def run_lua(self,code):
        self.lua.execute(code)

    def saved(self):
        return (self.data/'WoodUtilities.settings.ini').read_text(encoding='utf-8')

    def test_boot_mode_music_and_no_repeated_native_mode_calls(self):
        self.run_lua("assert(gi['Speedrun?'] and gi['SpeedrunMusic?']);assert(runner_calls==1)")
        self.run_lua("for i=1,100 do tick() end;assert(runner_calls==1)")
        self.run_lua("click_widget(control('Speedrunner music'));assert(not gi['SpeedrunMusic?'])")
        self.run_lua('assert(overrides.Speedrun==0 and overrides.DreamSpeedrunMusic==0 and not widget.Music:IsChecked() and music_events==1)')
        self.assertIn('speedrunner_music=false',self.saved())
        self.run_lua("click_widget(control('Auto-speedrunner mode'));assert(gi['Speedrun?']);gi['Speedrun?']=false")
        self.run_lua("world='NewWorld';tick();assert(not gi['Speedrun?'])")
        self.assertIn('auto_speedrunner=false',self.saved())

    def test_audio_hierarchy_mute_new_classes_and_world_travel(self):
        self.run_lua("slider_value('Master volume',0.5);slider_value('Music volume',0.4);slider_value('Effects volume',0.3);slider_value('Voice volume',0.2)")
        self.run_lua("assert(overrides.Master==0.5 and overrides.Music==0.4 and overrides.SFX==0.3 and overrides.Normal_Attack==1 and overrides.Voice==0.2)")
        self.run_lua("assert(overrides.Speedrun==0 and math.abs(overrides.DreamSpeedrunMusic-0.2)<0.001)")
        self.run_lua("assert(speedrun.Properties.Volume==0);assert(math.abs(overrides.NeverMute-0.15)<0.001)")
        self.run_lua("click_widget(control('Mute all audio'));assert(overrides.Master==0 and overrides.Speedrun==0 and overrides.NeverMute==0)")
        self.run_lua("click_widget(control('Mute all audio'));assert(overrides.Master==0.5)")
        self.run_lua("sound_class('ExtraAttack',fx);for i=1,31 do tick() end;assert(overrides.ExtraAttack==1);assert(speech.SoundClassObject==voice and footstep.SoundClassObject==fx and title.SoundClassObject==music_class)")
        self.run_lua("world='NextWorld';tick();assert(overrides.Master==0.5)")
        self.assertIn('master_volume=0.5',self.saved())

    def test_mouse_scaling_inversion_smoothing_and_player_isolation(self):
        self.run_lua("slider_value('Horizontal sensitivity',2);slider_value('Vertical sensitivity',0.5);click_widget(control('Invert vertical look'));click_widget(control('Mouse smoothing'))")
        self.run_lua("assert(hook_count==4 and not input_settings.bEnableMouseSmoothing)")
        self.run_lua("assert(input_value('/Script/Engine.PlayerController:AddYawInput',pc,3)==6)")
        self.run_lua("assert(input_value('/Script/Engine.PlayerController:AddPitchInput',pc,3)==-1.5)")
        self.run_lua("pawn=object('Pawn');pawn.Controller=pc;assert(input_value('/Script/Engine.Pawn:AddControllerYawInput',pawn,3)==6)")
        self.run_lua("other=object('PlayerController');function other:GetFullName() return 'OtherPlayer' end;assert(input_value('/Script/Engine.PlayerController:AddYawInput',other,3)==3)")
        self.run_lua("world='NextWorld';tick();assert(hook_count==4)")
        self.assertIn('sensitivity_x=2.0',self.saved())
        self.assertIn('invert_y=true',self.saved())

    def test_native_volume_does_not_compound_and_respects_vanilla_changes(self):
        self.run_lua("slider_value('Master volume',0.5);for i=1,100 do tick() end;assert(overrides.Master==0.5)")
        self.run_lua("dream.Properties.Volume=0;for i=1,31 do tick() end;assert(overrides.DreamSpeedrunMusic==0)")
        self.run_lua("click_widget(control('Mute all audio'));click_widget(control('Mute all audio'));assert(overrides.Master==0.5 and overrides.DreamSpeedrunMusic==0)")

    def test_reset_and_page_cleanup_preserve_time_warp(self):
        self.run_lua("slider_value('Music volume',0.2);old_slider=control('Music volume');assert(click('Reset audio'));assert(overrides.Music==1)")
        self.run_lua("slider_value('Horizontal sensitivity',3);click_widget(control('Invert horizontal look'));assert(click('Reset mouse'));assert(input_value('/Script/Engine.PlayerController:AddYawInput',pc,2)==2)")
        self.run_lua("assert(click('Time Warp'));assert(#test_ui.controls==0);old_slider:SetValue(0);tick();assert(overrides.Music==1 and applied_speed==1)")
        self.assertFalse((self.data/'settings.ini').exists())

    def test_saved_preferences_reload_and_corrupt_numbers_are_bounded(self):
        path=self.data/'WoodUtilities.settings.ini'
        path.write_text('auto_speedrunner=false\nsensitivity_x=nan\nsensitivity_y=99\nmaster_volume=-5\n',encoding='utf-8')
        self.run_lua("assert(click('Wood Utilities'));world='NextWorld';tick();assert(overrides.Master==0)")
        self.run_lua("assert(input_value('/Script/Engine.PlayerController:AddYawInput',pc,1)==1)")
        self.run_lua("assert(input_value('/Script/Engine.PlayerController:AddPitchInput',pc,1)==3)")


if __name__=='__main__':
    unittest.main()
