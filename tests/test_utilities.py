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
classes={};hook_count=0
function sound_class(name,volume)
 local sc=object('SoundClass');sc.name=name;sc.Properties={Volume=volume or 1}
 function sc:GetFullName() return 'SoundClass /Game/'..self.name end
 table.insert(classes,sc);return sc
end
speedrun=sound_class('Speedrun',0);dream=sound_class('DreamSpeedrunMusic')
master_output=object('SoundSubmix');volume_calls=0
function master_output:SetSubmixOutputVolume(context,value) assert(context==pc);application_gain=value;volume_calls=volume_calls+1 end
input_settings.bEnableLegacyInputScales=false
function pc:GetAddress() return 'controller-address' end
pc.InputYawScale=2.5;pc.InputPitchScale=-2.5
function pc:SetDeprecatedInputYawScale(value) self.InputYawScale=value end
function pc:SetDeprecatedInputPitchScale(value) self.InputPitchScale=value end
gameplay=object('GameplayStatics')
function gameplay:GetGameInstance() return gi end
widget=object('WB_TUNG_SETTINGS3_C');widget.Music=object('CheckBox');widget.Music.checked=true
function widget.Music:IsChecked() return self.checked end
function widget.Music:SetIsChecked(value) self.checked=value end
music_events=0
function widget:BndEvt__WB_TUNG_SETTINGS3_music_K2Node_ComponentBoundEvent_1_OnCheckBoxComponentStateChanged__DelegateSignature(value) music_events=music_events+1 end
local original_find=StaticFindObject
function StaticFindObject(path)
 if path=='/Script/Engine.Default__GameplayStatics' then return gameplay end
 if path=='/Script/Engine.Default__InputSettings' then return input_settings end
 if path=='/Engine/EngineSounds/Submixes/MasterSubmixDefault.MasterSubmixDefault' then return master_output end
 return original_find(path)
end
function FindAllOf(class)
 if class=='SoundClass' then return classes end
 if class=='WB_TUNG_SETTINGS3_C' then return {widget} end
 return {}
end
function RegisterHook() hook_count=hook_count+1;error('Input hooks must not be installed') end
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
        self.run_lua('assert(speedrun.Properties.Volume==0 and dream.Properties.Volume==0 and not widget.Music:IsChecked() and music_events==1)')
        self.assertIn('speedrunner_music=false',self.saved())
        self.run_lua("click_widget(control('Auto-speedrunner mode'));assert(gi['Speedrun?']);gi['Speedrun?']=false")
        self.run_lua("world='NewWorld';tick();assert(not gi['Speedrun?'])")

    def test_one_volume_controls_final_output_and_survives_world_travel(self):
        self.run_lua("slider_value('Application volume',0.37);assert(application_gain==0.37)")
        self.run_lua("slider_value('Application volume',0);assert(application_gain==0)")
        self.run_lua("slider_value('Application volume',1);world='NextWorld';tick();assert(application_gain==1)")
        self.run_lua("for i=1,100 do tick() end;assert(application_gain==1)")
        self.assertIn('application_volume=1',self.saved())

    def test_mouse_scaling_without_any_native_input_hooks(self):
        self.run_lua("slider_value('Horizontal sensitivity',3);slider_value('Vertical sensitivity',3)")
        self.run_lua("assert(hook_count==0 and pc.InputYawScale==3 and pc.InputPitchScale==3 and input_settings.bEnableLegacyInputScales)")
        self.run_lua("click_widget(control('Invert vertical look'));click_widget(control('Mouse smoothing'))")
        self.run_lua("assert(pc.InputPitchScale==-3 and not input_settings.bEnableMouseSmoothing)")
        self.run_lua("for i=1,50 do slider_value('Horizontal sensitivity',i%2==0 and 3 or 0.1) end;assert(hook_count==0 and pc.InputYawScale==3)")
        self.run_lua("world='NextWorld';tick();assert(pc.InputYawScale==3 and pc.InputPitchScale==-3)")

    def test_native_volume_does_not_compound_and_respects_vanilla_music_changes(self):
        self.run_lua("slider_value('Application volume',0.5);for i=1,100 do tick() end;assert(application_gain==0.5)")
        self.run_lua("dream.Properties.Volume=0;for i=1,31 do tick() end;assert(dream.Properties.Volume==0)")

    def test_reset_and_page_cleanup_preserve_time_warp(self):
        self.run_lua("slider_value('Application volume',0.2);old_slider=control('Application volume');assert(click('Reset audio'));assert(application_gain==1)")
        self.run_lua("slider_value('Horizontal sensitivity',3);click_widget(control('Invert horizontal look'));assert(click('Reset mouse'));assert(pc.InputYawScale==1)")
        self.run_lua("assert(click('Time Warp'));assert(#test_ui.controls==0);old_slider:SetValue(0);tick();assert(application_gain==1 and applied_speed==1)")
        self.assertFalse((self.data/'settings.ini').exists())

    def test_legacy_mute_migration_and_corrupt_numbers_are_bounded(self):
        path=self.data/'WoodUtilities.settings.ini'
        path.write_text('auto_speedrunner=false\nsensitivity_x=nan\nsensitivity_y=99\nmaster_volume=0.5\nmute=true\n',encoding='utf-8')
        self.run_lua("assert(click('Wood Utilities'));world='NextWorld';tick();assert(application_gain==0)")
        self.run_lua("assert(pc.InputYawScale==1 and pc.InputPitchScale==3)")
        self.run_lua("keys.F10();assert(click('Wood Utilities'));slider_value('Application volume',0.6);assert(application_gain==0.6)")
        self.assertIn('application_volume=0.6',self.saved())


if __name__=='__main__':
    unittest.main()
