-- Native UMG mod menu. Every call is made from Wood's game-thread dispatcher.
-- Hosts settings pages supplied by mods; has no knowledge of any specific mod.
return function(options)
    local ui = {visible=false, query='', filter='All', selected=nil, tab='Settings',
        actions={shell={},list={},details={}}, list_buttons={}, shown={}, controls={}, page=1, page_size=20}
    local icon_cache = {}
    local class_cache = {}
    local c = {
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
    local function put(o, label) if valid(o) then o:SetText(FText(label)) end end
    local function rounded(brush,radius,tint,outline)
        brush.DrawAs=4
        brush.TintColor=slate(tint)
        brush.OutlineSettings.CornerRadii={X=radius,Y=radius,Z=radius,W=radius}
        brush.OutlineSettings.RoundingType=0
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
        if not valid(class_cache[class]) then class_cache[class]=StaticFindObject('/Script/UMG.' .. class) end
        return StaticConstructObject(class_cache[class], outer or self.tree, 0,0,0,false,false,nil)
    end
    function ui:text(label, size, color, outer)
        local o=self:construct('TextBlock',outer)
        put(o,label)
        local font=o.Font; font.Size=size or 16; o:SetFont(font)
        o:SetColorAndOpacity(slate(color or c.white)); o:SetAutoWrapText(true)
        return o
    end
    function ui:logo(size, outer)
        if not options.logoPath or not options.loadIcon then return nil end
        local ok, texture=pcall(options.loadIcon, options.logoPath)
        if not ok or not valid(texture) then return nil end
        local image=self:construct('Image',outer)
        image:SetBrushFromTexture(texture,true)
        local box=self:construct('SizeBox',outer)
        box:SetWidthOverride(size); box:SetHeightOverride(size); box:AddChild(image)
        return box
    end
    local function row(parent, child, padding)
        local slot=parent:AddChildToVerticalBox(child)
        slot:SetPadding({Left=0,Top=padding or 5,Right=0,Bottom=padding or 5})
        return child
    end
    function ui:label(parent,label,size) return row(parent,self:text(label,size)) end
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
    function ui:add_toggle(parent,label,initial,callback)
        local line=self:construct('HorizontalBox'); row(parent,line,8)
        local text=self:text(label,15)
        line:AddChildToHorizontalBox(text):SetSize({Value=1,SizeRule=1})
        local val=initial==true
        local button,caption
        button,caption=self:button(line,val and 'On' or 'Off',function()
            val=not val; callback(val)
            put(caption,val and 'On' or 'Off')
            button:SetBackgroundColor(val and c.selected or c.rail)
        end)
        button:SetBackgroundColor(val and c.selected or c.rail)
        button:SetToolTipText(FText(label))
        return button
    end
    function ui:add_slider(parent,label,low,high,step,initial,callback,format)
        local function rounded_value(v)
            return math.max(low,math.min(high,math.floor((v-low)/step+0.5)*step+low))
        end
        local control={value=rounded_value(initial),callback=callback}
        local caption=row(parent,self:text('',15),6)
        local function update(v)
            v=rounded_value(v)
            if math.abs(v-control.value)<step/2 then return end
            control.value=v; control.widget:SetValue(v)
            put(caption,label..'  /  '..(format and format(v) or tostring(v)))
            callback(v)
        end
        put(caption,label..'  /  '..(format and format(control.value) or tostring(control.value)))
        local line=self:construct('HorizontalBox'); row(parent,line,5)
        self:button(line,'-',function() update(control.value-step) end)
        local slider=self:construct('Slider')
        slider:SetMinValue(low); slider:SetMaxValue(high); slider:SetStepSize(step)
        slider:SetValue(control.value); slider:SetSliderBarColor(c.selected); slider:SetSliderHandleColor(c.purple)
        slider:SetToolTipText(FText(label))
        local slot=line:AddChildToHorizontalBox(slider)
        slot:SetSize({Value=1,SizeRule=1}); slot:SetPadding({Left=14,Top=8,Right=14,Bottom=8})
        self:button(line,'+',function() update(control.value+step) end)
        control.widget=slider; control.update=update
        table.insert(self.controls,control)
        return slider
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
        local style=o.WidgetStyle
        local font_ok=pcall(function() style.TextStyle.Font.Size=15 end)
        if not font_ok then style.Font.Size=15 end
        style.ForegroundColor=slate(c.white); style.BackgroundColor=slate(c.ink)
        rounded(style.BackgroundImageNormal,5,{R=1,G=1,B=1,A=1})
        rounded(style.BackgroundImageHovered,5,{R=1,G=1,B=1,A=1},1)
        rounded(style.BackgroundImageFocused,5,{R=1,G=1,B=1,A=1},2)
        style.FocusedForegroundColor=slate(c.white)
        o.ClearKeyboardFocusOnCommit=false; o.SelectAllTextWhenFocused=true
        o:SetForegroundColor(c.white); o:SetHintText(FText(hint)); put(o,initial or '')
        border:SetContent(o); row(parent,border,5)
        return o
    end
    function ui:mod_list()
        if self.catalog then return self.catalog end
        local list = {}
        for _,definition in ipairs(options.mods) do
            list[#list+1] = {
                id=definition.id, name=definition.name or definition.id,
                version=definition.version or '1.0', author=definition.author or 'Unknown',
                description=definition.description or '', enabled=definition.enabled,
                error=definition.error,
                iconPath=definition.iconPath,
                configurable=definition.enabled and type(definition.buildSettings)=='function',
                definition=definition,
                badge=(definition.name or definition.id):sub(1,2):upper()
            }
        end
        self.catalog = list
        return list
    end
    function ui:find(id)
        for _,mod in ipairs(self:mod_list()) do if mod.id==id then return mod end end
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
        self.focus_widget=nil
        self.list:ClearChildren(); self.actions.list={}; self.list_buttons={}; self.shown={}
        local query=self.query:lower():sub(1,128)
        local all=self:mod_list()
        local matches={}
        for _,mod in ipairs(all) do
            local found=(mod.name..' '..mod.id..' '..mod.description):lower():find(query,1,true)
            if found and (self.filter=='All' or self.filter=='Active' and mod.enabled
                or self.filter=='Settings' and mod.configurable) then
                matches[#matches+1]=mod
            end
        end
        local page_count=math.max(1,math.ceil(#matches/self.page_size))
        self.page=math.min(self.page,page_count)
        local first=(self.page-1)*self.page_size+1
        local last=math.min(#matches,first+self.page_size-1)
        for index=first,last do
                local mod=matches[index]
                self.shown[#self.shown+1]=mod.id
                local item=self:construct('Button'); self:skin_button(item); item:SetBackgroundColor(c.card)
                local contents=self:construct('HorizontalBox')
                local content_slot=item:AddChild(contents)
                content_slot:SetPadding({Left=12,Top=12,Right=12,Bottom=12}); content_slot:SetHorizontalAlignment(0)
                local icon=self:construct('Border'); icon:SetBrushColor(c.selected)
                icon:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
                rounded(icon.Background,7,{R=1,G=1,B=1,A=1})
                local texture
                if mod.iconPath and options.loadIcon then
                    if icon_cache[mod.iconPath] == nil or icon_cache[mod.iconPath] and not valid(icon_cache[mod.iconPath]) then
                        local ok, result = pcall(options.loadIcon, mod.iconPath)
                        if ok and result then
                            icon_cache[mod.iconPath] = result
                        else
                            icon_cache[mod.iconPath] = false
                            print('[Wood] Could not load mod icon ' .. mod.iconPath .. ': ' .. tostring(result) .. '\n')
                        end
                    end
                    texture = icon_cache[mod.iconPath]
                end
                if valid(texture) then
                    local image=self:construct('Image')
                    local ok, err=pcall(function() image:SetBrushFromTexture(texture,true) end)
                    if ok then
                        local box=self:construct('SizeBox')
                        box:SetWidthOverride(128); box:SetHeightOverride(128)
                        local scale=self:construct('ScaleBox')
                        scale:SetStretch(1) -- ScaleToFit preserves the texture's aspect ratio.
                        scale:AddChild(image)
                        box:AddChild(scale)
                        icon:SetContent(box)
                    else
                        print('[Wood] Could not display mod icon ' .. mod.iconPath .. ': ' .. tostring(err) .. '\n')
                        icon:SetPadding({Left=10,Top=9,Right=10,Bottom=9})
                        icon:SetContent(self:text(mod.badge,15,c.purple))
                    end
                else
                    icon:SetPadding({Left=10,Top=9,Right=10,Bottom=9})
                    icon:SetContent(self:text(mod.badge,15,c.purple))
                end
                local icon_slot=contents:AddChildToHorizontalBox(icon)
                icon_slot:SetSize({Value=1,SizeRule=0})
                icon_slot:SetPadding({Left=0,Top=0,Right=12,Bottom=0})
                icon_slot:SetVerticalAlignment(1)
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
        local shown_first=#matches>0 and first or 0
        local shown_last=#matches>0 and last or 0
        put(self.result_count,string.format('%d-%d of %d mods',shown_first,shown_last,#matches))
        put(self.page_status,string.format('Page %d of %d',self.page,page_count))
        self.page_previous:SetIsEnabled(self.page>1)
        self.page_next:SetIsEnabled(self.page<page_count)
        if #matches==0 then
            row(self.list,self:text('No mods installed',18),12)
            row(self.list,self:text('Drop .lua or .tungmod files into the Mods folder and restart TUNG.',14,c.muted),4)
            if #all>0 then
                local buttons=self:construct('HorizontalBox'); row(self.list,buttons,12)
                self:button(buttons,'Reset filters',function() self.query=''; self.filter='All'; self.page=1; put(self.search,''); self:render_list() end,'list')
            end
        end
        self:paint_selection()
    end
    function ui:select(id,tab)
        self.selected=id; self.tab=tab or 'Settings'; self:render_details(); self:paint_selection()
    end
    function ui:render_details()
        self.focus_widget=nil
        self.refresh_pending=nil
        self.details:ClearChildren(); self.actions.details={}; self.controls={}
        local panel=self.details; local mod=self:find(self.selected)
        if self.notice then row(panel,self:text(self.notice,14,c.error),8) end
        if not mod then
            row(panel,self:text('YOUR MODS',28),12)
            row(panel,self:text('Drop .lua or .tungmod files into the Mods folder.',18,c.purple),6)
            local welcome=self:card(panel)
            row(welcome,self:text('Select a mod from the list',21),8)
            row(welcome,self:text('Its settings open here, inside TUNG.',16,c.muted),8)
            row(panel,self:text('F10 opens or closes Wood. Esc returns to this list.',13,c.muted),12)
            return
        end
        local back=self:construct('HorizontalBox'); row(panel,back,1)
        self:button(back,'< Mods',function() self:select(nil) end)
        row(panel,self:text(mod.name,27),7)
        row(panel,self:text('v'..mod.version..'  /  '..mod.author..'  /  '..(mod.error and 'Load error' or mod.enabled and 'Active' or 'Disabled'),13,c.purple),3)
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
            row(about,self:text('Drop or delete the .lua or .tungmod file from the Mods folder to install or remove this mod.',14,c.muted),8)
        elseif mod.error then
            local error_card=self:card(panel)
            row(error_card,self:text('This mod could not load',20,c.error),6)
            row(error_card,self:text(mod.error,14,c.muted),8)
            row(error_card,self:text('Check the mod file and restart TUNG. Other mods remain available.',14),8)
        elseif not mod.enabled then
            local notice=self:card(panel)
            row(notice,self:text('This mod is disabled',20),6)
            row(notice,self:text(options.speedrun and options.speedrun()
                and 'Speedrun mode prevents this mod from running. Settings are unavailable.'
                or 'This mod is unavailable in the current session.',15,c.muted),8)
        elseif mod.configurable then
            local contents=self:card(panel)
            local ok,err=pcall(mod.definition.buildSettings,options.mod_api(mod.definition),contents)
            if not ok then row(contents,self:text('Settings error: '..tostring(err),14,c.error),8) end
        else
            row(panel,self:text('This mod has no configurable settings.',17),12)
        end
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
        local scaling=self:construct('ScaleBox'); scaling:SetStretch(2)
        scaling:AddChild(design); self.tree.RootWidget=scaling
        local header=self:construct('Border'); header:SetBrushColor(c.rail); header:SetPadding({Left=24,Top=16,Right=24,Bottom=16})
        local heading=self:construct('HorizontalBox'); header:SetContent(heading)
        local logo=self:logo(40)
        if logo then heading:AddChildToHorizontalBox(logo):SetPadding({Left=0,Top=0,Right=14,Bottom=0}) end
        heading:AddChildToHorizontalBox(self:text('WOOD  /  MODS',23,c.lime)):SetSize({Value=1,SizeRule=1})
        local ver=self:text('v'..options.version..'   /   TUNG',13,c.muted); ver:SetAutoWrapText(false)
        heading:AddChild(ver); shell:AddChild(header)
        if options.setSpeedrun then
            local mode=self:construct('HorizontalBox'); shell:AddChild(mode)
            mode:AddChildToHorizontalBox(self:text('Speedrun mode: changing this restarts TUNG',13,c.muted)):SetSize({Value=1,SizeRule=1})
            self:button(mode,options.speedrun() and 'Speedrun: On' or 'Speedrun: Off',function()
                options.setSpeedrun(not options.speedrun())
            end,'shell',true)
        end
        local columns=self:construct('HorizontalBox'); shell:AddChildToVerticalBox(columns):SetSize({Value=1,SizeRule=1})
        local left=self:construct('Border'); left:SetBrushColor(c.rail); left:SetPadding({Left=18,Top=16,Right=18,Bottom=16})
        columns:AddChildToHorizontalBox(left):SetSize({Value=0.34,SizeRule=1})
        local list_shell=self:construct('VerticalBox'); left:SetContent(list_shell)
        row(list_shell,self:text('MOD LIBRARY',12,c.purple),4)
        self.search=self:input(list_shell,'Search mods...',self.query,'shell')
        local filters=self:construct('HorizontalBox'); row(list_shell,filters,9); self.filter_buttons={}
        for _,name in ipairs({'All','Active','Settings'}) do
            local filter=name
            local b=self:button(filters,name,function() self.filter=filter; self.page=1; self:render_list() end,'shell')
            b.Slot:SetSize({Value=1,SizeRule=1}); b.Slot:SetPadding({Left=2,Top=0,Right=2,Bottom=0})
            self.filter_buttons[name]=b
        end
        self.result_count=row(list_shell,self:text('',12,c.muted),5)
        self.list_scroll=self:construct('ScrollBox'); list_shell:AddChildToVerticalBox(self.list_scroll):SetSize({Value=1,SizeRule=1})
        self.list=self:construct('VerticalBox'); self.list_scroll:AddChild(self.list)
        local pages=self:construct('HorizontalBox'); row(list_shell,pages,4)
        self.page_previous=self:button(pages,'Previous',function() self.page=math.max(1,self.page-1); self:render_list() end,'shell')
        self.page_status=self:text('',12,c.muted); pages:AddChildToHorizontalBox(self.page_status):SetSize({Value=1,SizeRule=1})
        self.page_next=self:button(pages,'Next',function() self.page=self.page+1; self:render_list() end,'shell')
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
        print('[Wood] Mod menu created\n')
    end
    function ui:show(pc)
        if self.visible then return end
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
    function ui:typing() return self.visible and focused(self.search) end
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
        if focused(self.search) then if key=='return' and self.shown[1] then self:select(self.shown[1]) end; return end
        for _,group in ipairs({'shell','list','details'}) do
            for _,action in ipairs(self.actions[group]) do
                if valid(action.widget) and action.widget:HasKeyboardFocus() then action.callback(); return end
            end
        end
    end
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
        if self.notice_pending then
            self.notice_pending=false
            self:render_details()
        end
        if self.refresh_pending then
            local selected=self.refresh_pending; self.refresh_pending=nil
            if selected==self.selected then self:render_details() end
        end
        local query=value(self.search):sub(1,128)
        if query~=self.query then self.query=query; self.page=1; self:render_list() end
        for _,control in ipairs(self.controls) do
            if valid(control.widget) then control.update(control.widget:GetValue()) end
            if self.refresh_pending then break end
        end
        self:update_focus()
    end
    function ui:invalidate()
        self:hide()
        if valid(self.widget) then self.widget:RemoveFromParent() end
        self.widget=nil; self.tree=nil; self.search=nil
        icon_cache={}
        self.actions={shell={},list={},details={}}; self.list_buttons={}; self.controls={}
        self.focus_widget=nil
        self.refresh_pending=nil
    end
    function ui:make_entry(pc)
        local widget=library():Create(pc,StaticFindObject('/Script/UMG.UserWidget'),pc)
        local outer=widget.WidgetTree; local button=self:construct('Button',outer); self:skin_button(button)
        local caption=self:text('Wood Mods  /  F10',16,c.lime,outer)
        caption:SetAutoWrapText(false); caption:SetJustification(1)
        local content=self:construct('HorizontalBox',outer)
        local logo=self:logo(32,outer)
        if logo then content:AddChildToHorizontalBox(logo):SetPadding({Left=0,Top=0,Right=10,Bottom=0}) end
        content:AddChildToHorizontalBox(caption):SetVerticalAlignment(1)
        button:AddChild(content):SetPadding({Left=12,Top=8,Right=12,Bottom=8})
        button:SetBackgroundColor(c.rail); outer.RootWidget=button
        widget:AddToViewport(9000); widget:SetDesiredSizeInViewport({X=260,Y=56})
        local size=StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
        widget:SetPositionInViewport({X=26,Y=size.Y-74},true)
        return widget,button
    end
    return ui
end
