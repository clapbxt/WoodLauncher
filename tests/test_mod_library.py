"""Exercise the actual native Lua UI against a reflected-widget/engine double."""
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
function dofile(path)
 if path:find('paths.lua',1,true) then return test_root end
 if path:find('menu.lua',1,true) then
  local factory=real_dofile(test_menu)
  return function(options) test_ui=factory(options);return test_ui end
 end
 if path:find('extensions.lua',1,true) then return {
  {id='Example',path='example',name='Example',description='A practice helper',enabled=true},
  {id='Disabled',path='disabled',name='Disabled',enabled=false},
  {id='ReadOnly',path='readonly',name='Read Only',enabled=true},
  {id='Broken',path='broken',name='Broken',enabled=true}} end
 if path=='example' then return {buildSettings=function(api,panel) builds=builds+1; api.button(panel,'Example settings',function() callbacks=callbacks+1 end) end} end
 if path=='disabled' then error('Disabled script must never execute') end
 if path=='readonly' then return {} end
 if path=='broken' then error('Example load failure') end
 return real_dofile(path)
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


class NativeMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wood-ui-')
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / '.wood'
        self.data.mkdir()
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().test_root = self.temp.name.replace('\\', '/')
        self.lua.globals().test_menu = str(Path('NativeMods/WoodRuntime/Scripts/menu.lua').resolve()).replace('\\', '/')
        self.lua.execute(BOOT)
        source = Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8')
        self.lua.execute("assert(load(..., '@NativeMods/WoodRuntime/Scripts/main.lua'))()", source)
        self.lua.execute('tick(); keys.F10()')

    def tearDown(self):
        self.lua.execute("assert(unsafe_style_calls==0, 'Do not resubmit a live owning FButtonStyle through UE4SS')")

    def run_lua(self, code):
        self.lua.execute(code)

    def test_library_stays_visible_and_detached_callbacks_are_removed(self):
        self.run_lua("assert(has_label(test_ui.details,'YOUR MODS'));assert(click('Example'));assert(builds==1)")
        self.run_lua("assert(click('Example settings'));old_button=find_button('Example settings');assert(callbacks==1)")
        self.run_lua("assert(click('Time Warp'));assert(test_ui.selected=='TimeWarp');assert(test_ui.list_buttons.Example)")
        self.run_lua('click_widget(old_button);assert(callbacks==1);assert(builds==1)')
        self.run_lua("assert(click('Disabled'));assert(has_label(test_ui.details,'This mod is disabled'))")
        self.run_lua("assert(click('Broken'));assert(has_label(test_ui.details,'This mod could not load'))")

    def test_search_filters_and_empty_state(self):
        self.run_lua("test_ui.search:SetText(FText('practice helper'));tick();assert(#test_ui.shown==1 and test_ui.shown[1]=='Example')")
        self.run_lua("test_ui.search:SetText(FText(''));tick();assert(click('Settings'));assert(#test_ui.shown==2)")
        self.run_lua("test_ui.search:SetText(FText('[?]'));tick();assert(#test_ui.shown==0);assert(has_label(test_ui.list,'No matching mods'))")
        self.run_lua("assert(click('Reset filters'));assert(#test_ui.shown==5);assert(test_ui.query=='' and test_ui.filter=='All')")

    def test_filter_focus_transitions_preserve_the_page_and_settings(self):
        self.run_lua("assert(click('Time Warp'));assert(click('2x'));old_row=test_ui.list_buttons.Example")
        saved=(self.data / 'settings.ini').read_bytes()
        self.run_lua("""
            for cycle=1,20 do
                for _,filter in ipairs({'Active','Settings','All'}) do
                    local button=test_ui.filter_buttons[filter]
                    focus(nil);button.focus=true;tick()
                    if cycle%2==0 then keys.RETURN();tick() else click_widget(button) end
                    local expected=filter=='All' and 5 or filter=='Active' and 3 or 2
                    assert(test_ui.filter==filter and #test_ui.shown==expected)
                    assert(test_ui.selected=='TimeWarp' and applied_speed==2)
                    assert(button.WidgetStyle.Normal.OutlineSettings.Width==2)
                    assert(unsafe_style_calls==0)
                end
            end
            focus(nil);click_widget(old_row)
            assert(test_ui.selected=='TimeWarp' and applied_speed==2)
        """)
        self.assertEqual(saved, (self.data / 'settings.ini').read_bytes())

    def test_exact_speed_validates_and_enter_applies(self):
        self.run_lua("assert(click('Time Warp'));focus(test_ui.speed_input)")
        for invalid in ('0', '4.01', 'nan', 'hello'):
            self.lua.globals().invalid_value = invalid
            self.run_lua("test_ui.speed_input:SetText(FText(invalid_value));keys.RETURN();assert(applied_speed==1)")
        self.run_lua("test_ui.speed_input:SetText(FText('1.37'));keys.RETURN();assert(applied_speed==1.37)")
        self.assertIn('speed=1.37', (self.data / 'settings.ini').read_text())

    def test_toggles_presets_and_typing_do_not_change_unrelated_settings(self):
        self.run_lua("assert(click('Time Warp'));assert(click('2x'));assert(applied_speed==2)")
        self.run_lua('click_widget(test_ui.enabled_button);assert(applied_speed==1)')
        self.assertIn('speed=2.00\nenabled=false', (self.data / 'settings.ini').read_text())
        self.run_lua("assert(click('0.25x'));assert(applied_speed==1);assert(has_label(test_ui.details,'0.25x'))")
        self.run_lua('click_widget(test_ui.enabled_button);assert(applied_speed==0.25)')
        self.run_lua('focus(test_ui.search);keys.F8();assert(applied_speed==0.25);keys.SPACE();assert(applied_speed==0.25)')
        self.run_lua('focus(nil);keys.F8();assert(applied_speed==0.5)')
        self.run_lua('click_widget(test_ui.travel_button)')
        self.assertIn('restore_on_travel=false', (self.data / 'settings.ini').read_text())

    def test_keyboard_focus_is_visible_and_activates_the_selected_control(self):
        self.run_lua("assert(click('Time Warp'));focus(nil);test_ui.enabled_button.focus=true;tick()")
        self.run_lua('assert(test_ui.enabled_button.WidgetStyle.Normal.OutlineSettings.Width==2)')
        self.run_lua("keys.SPACE();assert(pc.ignore_move);assert(has_label(test_ui.details,'v2.2.1  /  Wood  /  Disabled'))")
        self.run_lua('focus(nil);test_ui.travel_button.focus=true;tick()')
        self.run_lua('assert(test_ui.enabled_button.WidgetStyle.Normal.OutlineSettings.Width==0);assert(test_ui.travel_button.WidgetStyle.Normal.OutlineSettings.Width==2)')
        self.run_lua('keys.RETURN()')
        self.assertIn('enabled=false\nrestore_on_travel=false', (self.data / 'settings.ini').read_text())

    def test_fast_click_waits_for_slate_and_does_not_leak_into_another_page(self):
        self.run_lua("old=find_button('Open Time Warp');target=find_button('Example');old.hover=true;keys.CLICK();assert(test_ui.selected==nil)")
        self.run_lua("tick();old.hover=false;target.hover=true;tick();tick();assert(test_ui.selected=='Example' and builds==1)")
        self.run_lua("target.hover=false;test_ui.list_buttons.TimeWarp.hover=true;keys.CLICK();keys.ESCAPE();tick();tick();tick();assert(test_ui.selected==nil)")

    def test_escape_focus_world_travel_and_reopen(self):
        self.run_lua("assert(click('Time Warp'));keys.ESCAPE();assert(test_ui.selected==nil and test_ui.visible)")
        self.run_lua('keys.ESCAPE();assert(not test_ui.visible);assert(not pc.ignore_look and not pc.ignore_move and pc.bShowMouseCursor)')
        self.run_lua("keys.F10();assert(click('Example'));keys.F10();keys.F10();assert(test_ui.selected=='Example' and builds==1)")
        self.run_lua("old_widget=test_ui.widget;world='NextWorld';tick();assert(old_widget.removed and not test_ui.visible)")
        self.run_lua("keys.F10();assert(test_ui.widget~=old_widget and test_ui.selected=='Example')")

    def test_viewport_respects_dpi_and_resizing(self):
        self.run_lua('viewport={X=800,Y=600};dpi=1;test_ui:resize();assert(test_ui.widget.desired.X==760 and test_ui.widget.desired.Y==560)')
        self.run_lua('viewport={X=1600,Y=900};dpi=1.25;test_ui:resize();assert(test_ui.widget.desired.X==896 and test_ui.widget.desired.Y==624)')

    def test_failed_build_releases_partial_widgets_and_can_retry(self):
        self.run_lua('test_ui:invalidate(); original_construct=StaticConstructObject')
        self.run_lua("function StaticConstructObject(class,...) if class.class:find('EditableTextBox',1,true) then error('Native field unavailable') end; return original_construct(class,...) end")
        self.run_lua('keys.F10();assert(not test_ui.visible and test_ui.widget==nil and test_ui.search==nil)')
        self.run_lua('assert(not pc.ignore_look and not pc.ignore_move);tick()')
        self.run_lua('StaticConstructObject=original_construct;keys.F10();assert(test_ui.visible and test_ui.search)')


if __name__ == '__main__':
    unittest.main()
