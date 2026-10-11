"""Exercise Utilities through the actual native menu, lifecycle, and saved settings."""
from pathlib import Path
import tempfile
import unittest
from lupa.lua54 import LuaRuntime

BOOT = r'''
created={}; keys={}; builds=0; callbacks=0; unsafe_style_calls=0; world='TestWorld'; viewport={X=1280,Y=720}; dpi=1
function FText(t) return {ToString=function() return t end} end
function brush() return {OutlineSettings={}} end
function object(class)
 local o={class=class,Font={Size=18},children={},value=1,visibility=0,bShowMouseCursor=true,
  Background=brush(),WidgetStyle={Normal=brush(),Hovered=brush(),Pressed=brush(),Disabled=brush(),Font={},TextStyle={Font={}},ForegroundColor={},BackgroundColor={},BackgroundImageNormal=brush(),BackgroundImageHovered=brush(),BackgroundImageFocused=brush()}}
 function o:IsValid() return true end
 function o:AddChild(child)
  table.insert(self.children,child); child.parent=self; child.Slot=object('Slot'); return child.Slot
 end
 o.AddChildToVerticalBox=o.AddChild; o.AddChildToHorizontalBox=o.AddChild; o.AddChildToScrollBox=o.AddChild
 function o:SetContent(child) self.children={child};child.parent=self end
 function o:GetParent() return self.parent end
 function o:ClearChildren() self.children={} end
 function o:SetText(t) self.label=t:ToString() end
 function o:GetText() return FText(self.label or '') end
 function o:SetFont(f) self.Font=f end
 -- Copying a live owning style through the pinned UE4SS bridge can terminate TUNG.
 function o:SetStyle(s) unsafe_style_calls=unsafe_style_calls+1;error('Unsafe owning FButtonStyle resubmission') end
 function o:SetValue(v) self.value=v end
 function o:GetValue() return self.value end
 function o:SetVisibility(v) self.visibility=v end
 function o:IsHovered() return self.hover==true end
 function o:HasKeyboardFocus() return self.focus==true end
 function o:HasFocusedDescendants() return self.descendant_focus==true end
 function o:GetFullName() return world..'.PlayerController' end
 function o:GetViewportSize() return viewport end
 function o:GetViewportScale() return dpi end
 function o:GetGlobalTimeDilation() return applied_speed or 1 end
 function o:SetGlobalTimeDilation(pc,speed) applied_speed=speed end
 function o:SetIgnoreLookInput(v) self.ignore_look=v end
 function o:SetIgnoreMoveInput(v) self.ignore_move=v end
 function o:SetDesiredSizeInViewport(v) self.desired=v end
 function o:SetBackgroundColor(v) self.background=v end
 function o:SetIsEnabled(v) self.enabled=v end
 function o:RemoveFromParent() self.removed=true end
 function o:Create() local m=object('UserWidget');m.WidgetTree=object('WidgetTree');return m end
 for _,name in ipairs({'SetPadding','SetSize','SetHorizontalAlignment','SetBrushColor','SetColorAndOpacity','SetForegroundColor','SetHintText',
  'SetAutoWrapText','SetWidthOverride','SetHeightOverride','SetStretch','SetJustification','SetToolTipText','SetMinValue','SetMaxValue','SetStepSize',
  'SetSliderBarColor','SetSliderHandleColor','AddToViewport','SetAlignmentInViewport','SetPositionInViewport',
  'SetInputMode_GameAndUIEx','SetInputMode_GameOnly','SetInputMode_UIOnlyEx'}) do o[name]=function() end end
 table.insert(created,o);return o
end
pc=object('PlayerController')
function StaticFindObject(path) return object(path) end
function StaticConstructObject(class) return object(class.class) end
function FindFirstOf() return pc end
function CreateInvalidObject() return nil end
function ExecuteInGameThread(fn) fn() end
function RegisterKeyBind(key,fn) keys[key]=fn end
Key={F10='F10',ESCAPE='ESCAPE',LEFT_MOUSE_BUTTON='CLICK',RETURN='RETURN',SPACE='SPACE',F6='F6',F7='F7',F8='F8'}
function LoopAsync(ms,fn) tick=fn end
real_dofile=dofile
real_popen=io.popen
function dofile(path)
 if path:find('paths.lua',1,true) then return test_root end
 if path:find('menu.lua',1,true) then
  local factory=real_dofile(test_menu)
  return function(options) test_ui=factory(options);return test_ui end
 end
 return real_dofile(path)
end
function io.popen(cmd)
 if cmd:find('dir /b',1,true) and cmd:find('Mods',1,true) then
  return {lines=function() return coroutine.wrap(function() coroutine.yield('WoodUtilities.lua') end) end, close=function() end}
 end
 return real_popen(cmd)
end
function has_label(o,label)
 if o.label==label then return true end
 for _,child in ipairs(o.children) do if has_label(child,label) then return true end end
 return false
end
function focus(o)
 for _,widget in ipairs(created) do widget.focus=false;widget.descendant_focus=false end
 if o then o.descendant_focus=true end
end
function click_widget(widget)
 for _,o in ipairs(created) do o.hover=false end
 widget.hover=true; keys.CLICK();tick();tick();tick()
end
function find_button(label)
 for _,group in ipairs({'shell','list','details'}) do
  for _,action in ipairs(test_ui.actions[group]) do if has_label(action.widget,label) then return action.widget end end
 end
end
function click(label)
 local button=find_button(label);if not button then return false end
 click_widget(button);return true
end
'''

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
mouse_x={Sensitivity=0.07,bInvert=false};mouse_y={Sensitivity=0.07,bInvert=false}
input_settings.AxisConfig={ForEach=function(self,callback)
 for _,pair in ipairs({{'MouseX',mouse_x},{'MouseY',mouse_y}}) do
  local entry={AxisKeyName=FText(pair[1]),AxisProperties=pair[2]}
  callback(1,{get=function() return entry end})
 end
end}
live_mouse=object('PlayerInput');pc.PlayerInput=live_mouse;setter_calls=0
function live_mouse:SetMouseSensitivity(value) live_sensitivity=value;setter_calls=setter_calls+1 end
rebuilds=0
function input_settings:ForceRebuildKeymaps() rebuilds=rebuilds+1 end
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
        self.temp = tempfile.TemporaryDirectory(prefix='wood-utilities-')
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / '.wood'
        self.data.mkdir()
        self.mods_dir = Path(self.temp.name) / 'Mods'
        self.mods_dir.mkdir()
        # Create test mod files - copy the actual standalone mod.
        src = Path('Mods/WoodUtilities.lua').read_text(encoding='utf-8')
        (self.mods_dir / 'WoodUtilities.lua').write_text(src, encoding='utf-8')
        # Create mods_disabled.txt
        (self.data / 'mods_disabled.txt').write_text('', encoding='utf-8')

        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().test_root = self.temp.name.replace('\\', '/')
        self.lua.globals().test_menu = str(Path('NativeMods/WoodRuntime/Scripts/menu.lua').resolve()).replace('\\', '/')
        self.lua.execute(BOOT + ENGINE)
        source = Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8')
        self.lua.execute("assert(load(..., '@NativeMods/WoodRuntime/Scripts/main.lua'))()", source)
        self.lua.execute("tick(); keys.F10()")
        self.lua.execute("assert(click('Wood Utilities'))")

    def tearDown(self):
        self.lua.execute("assert(unsafe_style_calls==0, 'Do not resubmit a live owning FButtonStyle through UE4SS')")

    def run_lua(self, code):
        self.lua.execute(code)

    def saved(self):
        return (self.data / 'WoodUtilities.settings.ini').read_text(encoding='utf-8')

    def test_boot_mode_music_and_no_repeated_native_mode_calls(self):
        self.run_lua("assert(gi['Speedrun?'] and gi['SpeedrunMusic?']);assert(runner_calls==1)")
        self.run_lua("for i=1,100 do tick() end;assert(runner_calls==1)")
        self.run_lua("click_widget(control('Speedrunner music'));assert(not gi['SpeedrunMusic?'])")
        self.run_lua('assert(speedrun.Properties.Volume==0 and dream.Properties.Volume==0 and not widget.Music:IsChecked() and music_events==1)')
        self.assertIn('speedrunner_music=false', self.saved())
        self.run_lua("click_widget(control('Auto-speedrunner mode'));assert(gi['Speedrun?']);gi['Speedrun?']=false")
        self.run_lua("world='NewWorld';tick();assert(not gi['Speedrun?'])")

    def test_one_volume_controls_final_output_and_survives_world_travel(self):
        self.run_lua("slider_value('Application volume',0.37);assert(application_gain==0.37)")
        self.run_lua("slider_value('Application volume',0);assert(application_gain==0)")
        self.run_lua("slider_value('Application volume',1);world='NextWorld';tick();assert(application_gain==1)")
        self.run_lua("for i=1,100 do tick() end;assert(application_gain==1)")
        self.assertIn('application_volume=1', self.saved())

    def test_live_mouse_setter_without_hooks_or_other_mouse_changes(self):
        self.run_lua("slider_value('Sensitivity',3);assert(math.abs(live_sensitivity-0.21)<0.00001 and hook_count==0 and rebuilds==0)")
        self.run_lua("for i=1,50 do slider_value('Sensitivity',i%2==0 and 3 or 0.1) end;assert(math.abs(live_sensitivity-0.21)<0.00001)")
        self.run_lua("assert(mouse_x.Sensitivity==0.07 and mouse_y.Sensitivity==0.07 and not mouse_x.bInvert and not mouse_y.bInvert)")
        self.run_lua("assert(input_settings.bEnableMouseSmoothing and not input_settings.bEnableLegacyInputScales and pc.InputPitchScale==-2.5)")
        self.run_lua("world='NextWorld';tick();assert(math.abs(live_sensitivity-0.21)<0.00001)")

    def test_mouse_setter_retries_when_player_input_is_not_ready(self):
        self.run_lua("pc.PlayerInput.invalid=true;world='LoadingWorld';tick();pc.PlayerInput=object('PlayerInput')")
        self.run_lua("function pc.PlayerInput:SetMouseSensitivity(value) live_sensitivity=value end;for i=1,31 do tick() end;assert(live_sensitivity==0.07)")

    def test_native_volume_does_not_compound_and_respects_vanilla_music_changes(self):
        self.run_lua("slider_value('Application volume',0.5);for i=1,100 do tick() end;assert(application_gain==0.5)")
        self.run_lua("dream.Properties.Volume=0;for i=1,31 do tick() end;assert(dream.Properties.Volume==0)")

    def test_reset_and_page_cleanup_preserve_time_warp(self):
        self.run_lua("slider_value('Application volume',0.2);old_slider=control('Application volume');assert(click('Reset audio'));assert(application_gain==1)")
        self.run_lua("slider_value('Sensitivity',3);assert(click('Reset sensitivity'));assert(live_sensitivity==0.07)")
        self.assertFalse((self.data / 'settings.ini').exists())

    def test_legacy_mute_migration_and_corrupt_numbers_are_bounded(self):
        path = self.data / 'WoodUtilities.settings.ini'
        path.write_text('auto_speedrunner=false\nsensitivity_x=nan\nsensitivity_y=99\nmaster_volume=0.5\nmute=true\n', encoding='utf-8')
        self.run_lua("assert(click('Wood Utilities'));world='NextWorld';tick();assert(application_gain==0)")
        self.run_lua("assert(live_sensitivity==0.07)")
        self.run_lua("keys.F10();assert(click('Wood Utilities'));slider_value('Application volume',0.6);assert(application_gain==0.6)")
        self.assertIn('application_volume=0.6', self.saved())


if __name__ == '__main__':
    unittest.main()