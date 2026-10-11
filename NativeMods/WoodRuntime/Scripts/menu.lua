-- Native UMG presentation. Every call is made from Wood's game-thread dispatcher.
-- The library stays visible while each mod supplies its own settings page.
return function(options)
    local ui = {visible=false, query='', filter='All', selected=nil, tab='Settings',
        actions={shell={},list={},details={}}, list_buttons={}, shown={}}
    local c = {
        -- Unreal accepts linear colors; these render as Wood's charcoal/purple theme.
        ink={R=0.006,G=0.005,B=0.010,A=1}, rail={R=0.012,G=0.008,B=0.020,A=1},
        card={R=0.024,G=0.018,B=0.036,A=1}, selected={R=0.09,G=0.032,B=0.19,A=1},
        purple={R=0.40,G=0.19,B=0.93,A=1}, lime={R=0.56,G=0.90,B=0.14,A=1},
        muted={R=0.40,G=0.36,B=0.48,A=1}, white={R=0.94,G=0.93,B=0.98,A=1},
        error={R=1,G=0.52,B=0.47,A=1}
    }
    local function valid(o) return o and o:IsValid() end
    local function library() return StaticFindObject('/Script/UMG.Default__WidgetBlueprintLibrary') end
    local function slate(color) return {SpecifiedColor=color,ColorUseRule=0} end
    local function focused(o) return valid(o) and (o:HasKeyboardFocus() or o:HasFocusedDescendants()) end
    local function value(o) return o:GetText():ToString() end
    local function state() return options.state() end
    local function put(o, label)
        if valid(o) then o:SetText(FText(label)) end
    end
    local function rounded(brush,radius,tint,outline)
        brush.DrawAs=4 -- ESlateBrushDrawType.RoundedBox
        brush.TintColor=slate(tint)
        brush.OutlineSettings.CornerRadii={X=radius,Y=radius,Z=radius,W=radius}
        brush.OutlineSettings.RoundingType=0 -- FixedRadius
        brush.OutlineSettings.Width=outline or 0
        brush.OutlineSettings.Color=slate(c.purple)
    end
    function ui:skin_button(button)
        local style=button.WidgetStyle
        rounded(style.Normal,6,{R=1,G=1,B=1,A=1})
        rounded(style.Hovered,6,{R=1.25,G=1.25,B=1.25,A=1},1)
        rounded(style.Pressed,6,{R=0.75,G=0.75,B=0.75,A=1},1)
        rounded(style.Disabled,6,{R=0.45,G=0.45,B=0.45,A=1})
    end
    function ui:construct(class, outer)
        return StaticConstructObject(StaticFindObject('/Script/UMG.' .. class), outer or self.tree, 0,0,0,false,false,nil)
    end
    function ui:text(label, size, color, outer)
        local o=self:construct('TextBlock',outer)
        put(o,label)
        local font=o.Font; font.Size=size or 16; o:SetFont(font)
        o:SetColorAndOpacity(slate(color or c.white)); o:SetAutoWrapText(true)
        return o
    end
    local function row(parent, child, padding)
        local slot=parent:AddChildToVerticalBox(child)
        slot:SetPadding({Left=0,Top=padding or 5,Right=0,Bottom=padding or 5})
        return child
    end
    function ui:label(parent,label,size)
        return row(parent,self:text(label,size))
    end
    function ui:button(parent,label,callback,group,accent)
        local o=self:construct('Button'); self:skin_button(o)
        local caption=self:text(label,14,accent and c.ink or c.white)
        caption:SetJustification(1); caption:SetAutoWrapText(false)
        o:AddChild(caption):SetPadding({Left=12,Top=9,Right=12,Bottom=9})
        o:SetBackgroundColor(accent and c.lime or c.selected)
        parent:AddChild(o)
        if callback then table.insert(self.actions[group or 'details'],{widget=o,callback=callback})
        else o:SetIsEnabled(false) end
        return o,caption
    end
    function ui:add_button(parent,label,callback)
        local line=self:construct('HorizontalBox'); row(parent,line)
        return self:button(line,label,callback)
    end
    function ui:card(parent)
        local border=self:construct('Border'); border:SetBrushColor(c.card)
        rounded(border.Background,9,{R=1,G=1,B=1,A=1})
        border:SetPadding({Left=18,Top=12,Right=18,Bottom=12})
        local box=self:construct('VerticalBox'); border:SetContent(box); row(parent,border,7)
        return box
    end
    function ui:input(parent,hint,initial,group)
        local border=self:construct('Border'); border:SetBrushColor(c.ink)
        border:SetPadding({Left=8,Top=6,Right=8,Bottom=6})
        local o=self:construct('EditableTextBox')
        -- Style the actual native text box before Unreal builds its Slate widget.
        local style=o.WidgetStyle
        local font_ok=pcall(function() style.TextStyle.Font.Size=15 end)
        if not font_ok then style.Font.Size=15 end
        style.ForegroundColor=slate(c.white); style.BackgroundColor=slate(c.ink)
        rounded(style.BackgroundImageNormal,5,{R=1,G=1,B=1,A=1})
        rounded(style.BackgroundImageHovered,5,{R=1,G=1,B=1,A=1},1)
        rounded(style.BackgroundImageFocused,5,{R=1,G=1,B=1,A=1},2)
        style.FocusedForegroundColor=slate(c.white)
        o.ClearKeyboardFocusOnCommit=false
        o.SelectAllTextWhenFocused=true
        o:SetForegroundColor(c.white); o:SetHintText(FText(hint)); put(o,initial or '')
        border:SetContent(o); parent:AddChild(border)
        return o
    end
    function ui:mods()
        local mods={{id='TimeWarp',name='Time Warp',version=options.version,author='Wood',
            description='Slow down tricky sections, practice at your own pace, and return to normal speed.',
            badge='TW',enabled=state().enabled,configurable=true,builtin=true}}
        for _,definition in ipairs(options.extensions) do
            mods[#mods+1]={id=definition.id,name=definition.name or definition.id,
                version=definition.version or '1.0',author=definition.author or 'Local mod',
                description=definition.description or '',enabled=definition.enabled,error=definition.error,
                configurable=definition.enabled and type(definition.buildSettings)=='function',definition=definition,
                badge=(definition.name or definition.id):sub(1,2):upper()}
        end
        return mods
    end
    function ui:find(id)
        for _,mod in ipairs(self:mods()) do if mod.id==id then return mod end end
    end
    function ui:paint_selection()
        for id,button in pairs(self.list_buttons) do
            if valid(button) then button:SetBackgroundColor(id==self.selected and c.selected or c.card) end
        end
        for name,button in pairs(self.filter_buttons or {}) do
            button:SetBackgroundColor(name==self.filter and c.selected or c.card)
        end
    end
    function ui:render_list()
        self.list:ClearChildren(); self.actions.list={}; self.list_buttons={}; self.shown={}
        local query=self.query:lower():sub(1,128)
        local mods=self:mods()
        for _,mod in ipairs(mods) do
            local matches=(mod.name..' '..mod.id..' '..mod.description):lower():find(query,1,true)
            if matches and (self.filter=='All' or self.filter=='Active' and mod.enabled
                or self.filter=='Settings' and mod.configurable) then
                self.shown[#self.shown+1]=mod.id
                local item=self:construct('Button'); self:skin_button(item); item:SetBackgroundColor(c.card)
                local contents=self:construct('HorizontalBox')
                local content_slot=item:AddChild(contents)
                content_slot:SetPadding({Left=12,Top=12,Right=12,Bottom=12}); content_slot:SetHorizontalAlignment(0)
                local icon=self:construct('Border'); icon:SetBrushColor(c.selected)
                rounded(icon.Background,7,{R=1,G=1,B=1,A=1})
                icon:SetPadding({Left=10,Top=9,Right=10,Bottom=9})
                icon:SetContent(self:text(mod.badge,15,mod.builtin and c.lime or c.purple))
                contents:AddChildToHorizontalBox(icon):SetPadding({Left=0,Top=0,Right=12,Bottom=0})
                local words=self:construct('VerticalBox')
                contents:AddChildToHorizontalBox(words):SetSize({Value=1,SizeRule=1})
                row(words,self:text(mod.name,17),1)
                row(words,self:text('v'..mod.version..'  /  '..(mod.error and 'Load error' or mod.enabled and 'Active' or 'Disabled'),
                    12,mod.enabled and c.lime or c.muted),3)
                row(self.list,item,4)
                local id=mod.id
                self.actions.list[#self.actions.list+1]={widget=item,callback=function() self:select(id) end}
                self.list_buttons[id]=item
                item:SetToolTipText(FText('Open '..mod.name..' settings'))
            end
        end
        put(self.result_count,string.format('%d of %d mods',#self.shown,#mods))
        if #self.shown==0 then
            row(self.list,self:text('No matching mods',18),12)
            row(self.list,self:text('Try another name or reset your filters.',14,c.muted),4)
            local buttons=self:construct('HorizontalBox'); row(self.list,buttons,12)
            self:button(buttons,'Reset filters',function() self.query=''; self.filter='All'; put(self.search,''); self:render_list() end,'list')
        end
        self:paint_selection()
        self.list_state=tostring(state().enabled)
    end
    function ui:time_warp(panel)
        local speed_card=self:card(panel)
        local heading=self:construct('HorizontalBox'); row(speed_card,heading,2)
        heading:AddChildToHorizontalBox(self:text('SELECTED SPEED',12,c.muted)):SetSize({Value=1,SizeRule=1})
        self.speed_label=self:text('',30,c.lime); heading:AddChild(self.speed_label)
        self.applied_label=row(speed_card,self:text('',13,c.muted),4)
        self.slider=self:construct('Slider')
        self.slider:SetMinValue(0.05); self.slider:SetMaxValue(4); self.slider:SetStepSize(0.05)
        self.slider:SetValue(state().speed); self.slider:SetSliderBarColor(c.selected); self.slider:SetSliderHandleColor(c.purple)
        row(speed_card,self.slider,12)
        local presets={0.1,0.25,0.5,1,2,4}; self.presets={}
        for offset=1,6,3 do
            local line=self:construct('HorizontalBox'); row(speed_card,line,3)
            for i=offset,offset+2 do
                local target=presets[i]
                local button=self:button(line,string.format('%gx',target),function() options.set_speed(target) end)
                button.Slot:SetSize({Value=1,SizeRule=1})
                button.Slot:SetPadding({Left=3,Top=0,Right=3,Bottom=0})
                self.presets[#self.presets+1]={widget=button,value=target}
            end
        end
        local exact=self:construct('HorizontalBox'); row(speed_card,exact,8)
        self.speed_input=self:input(exact,'Exact speed, 0.05 to 4',string.format('%.2f',state().speed))
        self.speed_input:GetParent().Slot:SetSize({Value=1,SizeRule=1})
        local apply=self:button(exact,'Apply',function() self:apply_exact() end)
        apply.Slot:SetPadding({Left=8,Top=0,Right=0,Bottom=0})
        self.validation=row(speed_card,self:text('Enter a speed from 0.05 to 4. Press Enter to apply.',12,c.muted),2)
        local preferences=self:card(panel)
        local function toggle(title,description,callback)
            local line=self:construct('HorizontalBox'); row(preferences,line,5)
            local words=self:construct('VerticalBox'); line:AddChildToHorizontalBox(words):SetSize({Value=1,SizeRule=1})
            row(words,self:text(title,16),1); row(words,self:text(description,12,c.muted),2)
            local button,caption=self:button(line,'',callback)
            button.Slot:SetPadding({Left=14,Top=3,Right=0,Bottom=3})
            return button,caption
        end
        self.enabled_button,self.enabled_label=toggle('Time Warp','Off restores normal speed and keeps your chosen value.',
            function() options.set_enabled(not state().enabled) end)
        self.travel_button,self.travel_label=toggle('Reset on world change','Return to 1x when loading another world.',
            function() options.set_travel(not state().restore_on_travel) end)
        local reset=self:construct('HorizontalBox'); row(panel,reset,7)
        self:button(reset,'Reset speed to 1x',function() options.set_speed(1) end)
        row(panel,self:text('F6  Slower     F7  Normal     F8  Faster',13,c.purple),4)
        row(panel,self:text('Changes save automatically. Use these controls for practice.',12,c.muted),4)
        self.last_values=nil; self:refresh_timewarp()
    end
    function ui:apply_exact()
        if not valid(self.speed_input) then return end
        local number=tonumber(value(self.speed_input))
        if not number or number~=number or number<0.05 or number>4 then
            put(self.validation,'Use a number from 0.05 to 4, such as 0.25 or 1.5.')
            self.validation:SetColorAndOpacity(slate(c.error)); return
        end
        options.set_speed(number)
        put(self.speed_input,string.format('%.2f',state().speed))
        put(self.validation,'Speed saved.'); self.validation:SetColorAndOpacity(slate(c.lime))
    end
    function ui:refresh_timewarp()
        local s=state()
        if valid(self.mod_status) then
            local metadata=self.status_prefix..(s.enabled and 'Active' or 'Disabled')
            if metadata~=self.last_metadata then put(self.mod_status,metadata); self.last_metadata=metadata end
        end
        if not valid(self.speed_label) then return end
        local signature=string.format('%.2f|%.2f|%s|%s',s.speed,s.applied,tostring(s.enabled),tostring(s.restore_on_travel))
        if signature==self.last_values then return end
        self.last_values=signature
        put(self.speed_label,string.format('%.2fx',s.speed))
        put(self.applied_label,s.enabled and string.format('Applied to the world: %.2fx',s.applied)
            or 'Disabled  /  world running at normal speed')
        self.slider:SetValue(s.speed)
        if not focused(self.speed_input) then put(self.speed_input,string.format('%.2f',s.speed)) end
        put(self.enabled_label,s.enabled and 'On' or 'Off'); put(self.travel_label,s.restore_on_travel and 'On' or 'Off')
        self.enabled_button:SetBackgroundColor(s.enabled and c.selected or c.rail)
        self.travel_button:SetBackgroundColor(s.restore_on_travel and c.selected or c.rail)
        for _,preset in ipairs(self.presets) do preset.widget:SetBackgroundColor(math.abs(preset.value-s.speed)<0.005 and c.selected or c.rail) end
    end
    function ui:select(id,tab)
        self.selected=id; self.tab=tab or 'Settings'; self:render_details(); self:paint_selection()
    end
    function ui:render_details()
        self.details:ClearChildren(); self.actions.details={}
        self.slider=nil; self.speed_label=nil; self.speed_input=nil; self.validation=nil
        self.mod_status=nil; self.last_metadata=nil
        local panel=self.details; local mod=self:find(self.selected)
        if not mod then
            row(panel,self:text('YOUR MODS',28),12)
            row(panel,self:text('A few good tools. A better next attempt.',18,c.purple),6)
            local welcome=self:card(panel)
            row(welcome,self:text('Select a mod from the list',21),8)
            row(welcome,self:text('Its settings open here, inside TUNG. Search by name or use the filters to find your tools.',16,c.muted),8)
            row(welcome,self:text('Time Warp is included. Start with a preset, then tune your speed.',15,c.muted),8)
            local quick=self:construct('HorizontalBox'); row(welcome,quick,12)
            self:button(quick,'Open Time Warp',function() self:select('TimeWarp') end,'details',true)
            row(panel,self:text('F10 opens or closes Wood. Esc returns to this list.',13,c.muted),12)
            return
        end
        local back=self:construct('HorizontalBox'); row(panel,back,1)
        self:button(back,'< Mods',function() self:select(nil) end)
        row(panel,self:text(mod.name,27),7)
        local metadata=row(panel,self:text('v'..mod.version..'  /  '..mod.author..'  /  '..(mod.error and 'Load error' or mod.enabled and 'Active' or 'Disabled'),13,c.purple),3)
        if mod.builtin then self.mod_status=metadata; self.status_prefix='v'..mod.version..'  /  '..mod.author..'  /  ' end
        if mod.description~='' then row(panel,self:text(mod.description,14,c.muted),6) end
        local tabs=self:construct('HorizontalBox'); row(panel,tabs,8)
        local settings=self:button(tabs,'Settings',mod.configurable and function() self:select(mod.id,'Settings') end or nil)
        settings:SetBackgroundColor(self.tab=='Settings' and c.selected or c.card)
        local info=self:button(tabs,'Info',function() self:select(mod.id,'Info') end)
        info.Slot:SetPadding({Left=6,Top=0,Right=0,Bottom=0})
        info:SetBackgroundColor(self.tab=='Info' and c.selected or c.card)
        if self.tab=='Info' then
            local about=self:card(panel)
            row(about,self:text('ABOUT THIS MOD',12,c.purple),5)
            row(about,self:text(mod.name,22),4)
            row(about,self:text('ID: '..mod.id..'\nVersion: '..mod.version..'\nAuthor: '..mod.author,15,c.muted),8)
            row(about,self:text(mod.description~='' and mod.description or 'No description supplied.',15),8)
            row(about,self:text(mod.builtin and 'Included with Wood. Settings apply immediately.' or 'Mod selection changes in the launcher apply after restarting TUNG.',14,c.muted),8)
        elseif mod.builtin then self:time_warp(panel)
        elseif mod.error then
            local error_card=self:card(panel)
            row(error_card,self:text('This mod could not load',20,c.error),6)
            row(error_card,self:text(mod.error,14,c.muted),8)
            row(error_card,self:text('Check the mod files and restart TUNG. Other mods remain available.',14),8)
        elseif not mod.enabled then
            local notice=self:card(panel)
            row(notice,self:text('This mod is disabled',20),6)
            row(notice,self:text('Enable it in Wood Launcher, then restart TUNG to load its settings.',15,c.muted),8)
        elseif mod.configurable then
            local contents=self:card(panel)
            local ok,err=pcall(mod.definition.buildSettings,options.extension_api(mod.definition),contents)
            if not ok then row(contents,self:text('Settings error: '..tostring(err),14,c.error),8) end
        else
            row(panel,self:text('This mod has no configurable settings.',17),12)
        end
        self:refresh_timewarp()
    end
    function ui:resize()
        if not valid(self.widget) then return end
        local layout=StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary')
        local size=layout:GetViewportSize(self.pc); local scale=layout:GetViewportScale(self.pc)
        if type(scale)~='number' or scale<=0 then scale=1 end
        self.widget:SetPositionInViewport({X=size.X/2,Y=size.Y/2},true)
        self.widget:SetDesiredSizeInViewport({X=math.min(1120,math.max(360,size.X-40))/scale,Y=math.min(780,math.max(300,size.Y-40))/scale})
    end
    function ui:build(pc)
        self.pc=pc; self.actions={shell={},list={},details={}}
        self.widget=library():Create(pc,StaticFindObject('/Script/UMG.UserWidget'),pc)
        assert(valid(self.widget),'Unreal did not create the mod menu')
        self.tree=self.widget.WidgetTree
        local border=self:construct('Border'); border:SetBrushColor(c.ink); border:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
        local shell=self:construct('VerticalBox'); border:SetContent(shell)
        local design=self:construct('SizeBox'); design:SetWidthOverride(1100); design:SetHeightOverride(700); design:AddChild(border)
        local scaling=self:construct('ScaleBox'); scaling:SetStretch(2) -- ScaleToFit preserves text and icon proportions.
        scaling:AddChild(design); self.tree.RootWidget=scaling
        local header=self:construct('Border'); header:SetBrushColor(c.rail); header:SetPadding({Left=24,Top=16,Right=24,Bottom=16})
        local heading=self:construct('HorizontalBox'); header:SetContent(heading)
        heading:AddChildToHorizontalBox(self:text('WOOD  /  MODS',23,c.lime)):SetSize({Value=1,SizeRule=1})
        local version=self:text('v'..options.version..'   /   TUNG',13,c.muted); version:SetAutoWrapText(false)
        heading:AddChild(version); shell:AddChild(header)
        local columns=self:construct('HorizontalBox'); shell:AddChildToVerticalBox(columns):SetSize({Value=1,SizeRule=1})
        local left=self:construct('Border'); left:SetBrushColor(c.rail); left:SetPadding({Left=18,Top=16,Right=18,Bottom=16})
        columns:AddChildToHorizontalBox(left):SetSize({Value=0.34,SizeRule=1})
        local list_shell=self:construct('VerticalBox'); left:SetContent(list_shell)
        row(list_shell,self:text('MOD LIBRARY',12,c.purple),4)
        self.search=self:input(list_shell,'Search mods...',self.query,'shell')
        local filters=self:construct('HorizontalBox'); row(list_shell,filters,9); self.filter_buttons={}
        for _,name in ipairs({'All','Active','Settings'}) do
            local filter=name
            local b=self:button(filters,name,function() self.filter=filter; self:render_list() end,'shell')
            b.Slot:SetSize({Value=1,SizeRule=1}); b.Slot:SetPadding({Left=2,Top=0,Right=2,Bottom=0})
            self.filter_buttons[name]=b
        end
        self.result_count=row(list_shell,self:text('',12,c.muted),5)
        self.list_scroll=self:construct('ScrollBox'); list_shell:AddChildToVerticalBox(self.list_scroll):SetSize({Value=1,SizeRule=1})
        self.list=self:construct('VerticalBox'); self.list_scroll:AddChild(self.list)
        local right=self:construct('Border'); right:SetBrushColor(c.ink); right:SetPadding({Left=24,Top=16,Right=24,Bottom=16})
        columns:AddChildToHorizontalBox(right):SetSize({Value=0.66,SizeRule=1})
        self.detail_scroll=self:construct('ScrollBox'); right:SetContent(self.detail_scroll)
        self.details=self:construct('VerticalBox'); self.detail_scroll:AddChild(self.details)
        local footer=self:construct('Border'); footer:SetBrushColor(c.rail); footer:SetPadding({Left=24,Top=12,Right=24,Bottom=12})
        local foot=self:construct('HorizontalBox'); footer:SetContent(foot)
        foot:AddChildToHorizontalBox(self:text('Esc  Back     /     F10  Close     /     Tab  Navigate',12,c.muted)):SetSize({Value=1,SizeRule=1})
        self:button(foot,'Back to game',function() self:hide() end,'shell',true); shell:AddChild(footer)
        self:render_list(); self:render_details()
        self.widget:AddToViewport(10000); self.widget:SetAlignmentInViewport({X=0.5,Y=0.5}); self.widget:SetVisibility(2)
        self:resize()
        print('[Wood] Native mod library created\n')
    end
    function ui:show(pc)
        if not valid(pc) then return end
        if not valid(self.widget) then
            local ok,err=pcall(function() self:build(pc) end)
            if not ok then self:invalidate(); error(err) end
        end
        self.pc=pc; self.saved_cursor=pc.bShowMouseCursor
        pc:SetIgnoreLookInput(true); pc:SetIgnoreMoveInput(true); pc.bShowMouseCursor=true
        self.widget:SetVisibility(0); self:resize(); library():SetInputMode_UIOnlyEx(pc,self.widget,0,false)
        self.visible=true
    end
    function ui:hide()
        if not self.visible then return end
        if valid(self.widget) then self.widget:SetVisibility(2) end
        self.visible=false
        if valid(self.pc) then
            self.pc:SetIgnoreLookInput(false); self.pc:SetIgnoreMoveInput(false); self.pc.bShowMouseCursor=self.saved_cursor==true
            if self.saved_cursor then library():SetInputMode_GameAndUIEx(self.pc,CreateInvalidObject(),0,false,false)
            else library():SetInputMode_GameOnly(self.pc,false) end
        end
    end
    function ui:escape()
        if not self.visible then return end
        if focused(self.search) and self.query~='' then
            self.query=''; put(self.search,''); self:render_list()
        elseif self.selected then self:select(nil)
        else self:hide() end
    end
    function ui:typing() return self.visible and (focused(self.search) or focused(self.speed_input)) end
    function ui:click()
        if not self.visible then return end
        for _,group in ipairs({'shell','list','details'}) do
            for _,action in ipairs(self.actions[group]) do
                if valid(action.widget) and action.widget:IsHovered() then action.callback(); return end
            end
        end
    end
    function ui:key(key)
        if not self.visible then return end
        if focused(self.speed_input) then if key=='return' then self:apply_exact() end; return end
        if focused(self.search) then if key=='return' and self.shown[1] then self:select(self.shown[1]) end; return end
        for _,group in ipairs({'shell','list','details'}) do
            for _,action in ipairs(self.actions[group]) do
                if valid(action.widget) and action.widget:HasKeyboardFocus() then action.callback(); return end
            end
        end
    end
    -- Mutate reflected brush fields in place. Resubmitting the owning FButtonStyle
    -- through UButton:SetStyle can fail-fast in the pinned UE4SS bridge.
    function ui:update_focus()
        local current
        for _,group in ipairs({'shell','list','details'}) do
            for _,action in ipairs(self.actions[group]) do
                if valid(action.widget) and action.widget:HasKeyboardFocus() then current=action.widget; break end
            end
            if current then break end
        end
        if current==self.focus_widget then return end
        if valid(self.focus_widget) then
            local style=self.focus_widget.WidgetStyle
            style.Normal.OutlineSettings.Width=0
            style.Hovered.OutlineSettings.Width=1; style.Hovered.OutlineSettings.Color=slate(c.purple)
        end
        self.focus_widget=current
        if current then
            local style=current.WidgetStyle
            style.Normal.OutlineSettings.Width=2; style.Normal.OutlineSettings.Color=slate(c.lime)
            style.Hovered.OutlineSettings.Width=2; style.Hovered.OutlineSettings.Color=slate(c.lime)
        end
    end
    function ui:tick()
        if not self.visible then return end
        local query=value(self.search):sub(1,128)
        if query~=self.query or self.list_state~=tostring(state().enabled) then self.query=query; self:render_list() end
        if valid(self.slider) then
            local number=math.floor(math.max(0.05,math.min(4,self.slider:GetValue()))*100+0.5)/100
            if number~=state().speed then options.set_speed(number) end
        end
        self:refresh_timewarp()
        self:update_focus()
    end
    function ui:invalidate()
        self:hide()
        if valid(self.widget) then self.widget:RemoveFromParent() end
        self.widget=nil; self.tree=nil; self.search=nil; self.slider=nil; self.speed_label=nil; self.speed_input=nil; self.mod_status=nil
        self.actions={shell={},list={},details={}}; self.list_buttons={}
        self.focus_widget=nil
    end
    function ui:make_entry(pc)
        local widget=library():Create(pc,StaticFindObject('/Script/UMG.UserWidget'),pc)
        local outer=widget.WidgetTree; local button=self:construct('Button',outer); self:skin_button(button)
        local caption=self:text('Wood Mods  /  F10',16,c.lime,outer)
        caption:SetAutoWrapText(false); caption:SetJustification(1)
        button:AddChild(caption):SetPadding({Left=12,Top=8,Right=12,Bottom=8})
        button:SetBackgroundColor(c.rail); outer.RootWidget=button
        widget:AddToViewport(9000); widget:SetDesiredSizeInViewport({X=260,Y=56})
        local size=StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
        widget:SetPositionInViewport({X=26,Y=size.Y-74},true)
        return widget,button
    end
    return ui
end
