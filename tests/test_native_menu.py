"""Run actual Lua UI logic against a minimal reflected-widget test double."""
from pathlib import Path
import unittest
from lupa.lua54 import LuaRuntime

BOOT = r'''
created={}; keys={}; builds=0; callbacks=0
function object(class)
 local o={class=class,Font={Size=18},children={},value=1,visibility=0,bShowMouseCursor=true}
 function o:IsValid() return true end
 function o:AddChild(child) table.insert(self.children,child); return object('Slot') end
 o.AddChildToVerticalBox=o.AddChild; o.AddChildToHorizontalBox=o.AddChild; o.AddChildToScrollBox=o.AddChild
 function o:SetContent(child) self.children={child} end
 function o:ClearChildren() self.children={} end
 function o:SetText(t) self.label=t end
 function o:SetFont(f) self.Font=f end
 function o:SetValue(v) self.value=v end
 function o:GetValue() return self.value end
 function o:SetVisibility(v) self.visibility=v end
 function o:IsHovered() return self.hover==true end
 function o:HasKeyboardFocus() return false end
 function o:GetFullName() return 'TestWorld.PlayerController' end
 function o:GetViewportSize() return {X=1280,Y=720} end
 function o:GetGlobalTimeDilation() return applied_speed or 1 end
 function o:SetGlobalTimeDilation(pc,speed) applied_speed=speed end
 function o:Create() local m=object('UserWidget');m.WidgetTree=object('WidgetTree');return m end
 for _,name in ipairs({'SetPadding','SetSize','SetBrushColor','SetColorAndOpacity','SetBackgroundColor','SetMinValue','SetMaxValue','SetStepSize','SetSliderBarColor','SetSliderHandleColor','AddToViewport','SetAlignmentInViewport','SetPositionInViewport','SetDesiredSizeInViewport','SetIgnoreLookInput','SetIgnoreMoveInput','SetInputMode_GameAndUIEx','SetInputMode_GameOnly','SetInputMode_UIOnlyEx','RemoveFromParent'}) do o[name]=function() end end
 table.insert(created,o);return o
end
pc=object('PlayerController')
function StaticFindObject(path) return object(path) end
function StaticConstructObject(class) return object(class.class) end
function FindFirstOf() return pc end
function FText(t) return t end
function CreateInvalidObject() return nil end
function ExecuteInGameThread(fn) fn() end
function RegisterKeyBind(key,fn) keys[key]=fn end
Key={F10='F10',ESCAPE='ESCAPE',LEFT_MOUSE_BUTTON='CLICK',RETURN='RETURN',SPACE='SPACE',F6='F6',F7='F7',F8='F8'}
function LoopAsync(ms,fn) tick=fn end
real_dofile=dofile
function dofile(path)
 if path:find('paths.lua',1,true) then return '.' end
 if path:find('extensions.lua',1,true) then return {{id='Example',path='example',name='Example',enabled=true},{id='Disabled',path='disabled',name='Disabled',enabled=false}} end
 if path=='example' then return {buildSettings=function(api,panel) builds=builds+1; api.button(panel,'Example settings',function() callbacks=callbacks+1 end) end} end
 if path=='disabled' then error('Disabled script must never execute') end
 return real_dofile(path)
end
function contains(label) for _,o in ipairs(created) do if o.label==label then return true end end return false end
function has_label(o,label)
 if o.label==label then return true end
 for _,child in ipairs(o.children) do if has_label(child,label) then return true end end
 return false
end
function click(label)
 for _,o in ipairs(created) do o.hover=false end
 for i=#created,1,-1 do local o=created[i]; if o.class:find('Button',1,true) and has_label(o,label) then o.hover=true;keys.CLICK();return true end end
 return false
end
'''


class NativeMenuTests(unittest.TestCase):
    def test_navigation_builds_only_selected_mod_and_clears_old_actions(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BOOT)
        source = Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8')
        lua.execute("assert(load(..., '@NativeMods/WoodRuntime/Scripts/main.lua'))()", source)
        lua.execute("tick(); keys.F10()")
        self.assertTrue(lua.eval("contains('YOUR MODS')"))
        self.assertEqual(lua.globals().builds, 0)
        self.assertTrue(lua.eval("click('Time Warp')"))
        lua.execute('tick()')
        self.assertTrue(lua.eval("contains('TIME WARP')"))
        self.assertEqual(lua.globals().builds, 0)
        lua.execute('keys.ESCAPE()')
        self.assertTrue(lua.eval("click('Example')"))
        self.assertEqual(lua.globals().builds, 1)
        self.assertTrue(lua.eval("click('Example settings')"))
        self.assertEqual(lua.globals().callbacks, 1)
        self.assertTrue(lua.eval("click('  < Back to mods  ')"))
        # Hovering a detached old widget must not dispatch its previous callback.
        lua.execute("click('Example settings')")
        self.assertEqual(lua.globals().callbacks, 1)
        self.assertTrue(lua.eval("click('Disabled')"))
        self.assertTrue(lua.eval("contains('Disabled. Enable in the launcher and restart TUNG.')"))
        self.assertEqual(lua.globals().builds, 1)


if __name__ == '__main__': unittest.main()
