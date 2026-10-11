-- Rename the folder and manifest id; folders beginning with _ are templates.
return {
    name = 'Example native mod',
    version = '1.0.0',
    description = 'A persistent setting inside Wood\'s native mod menu.',
    onWorldReady = function(api)
        api.log('Attached to ' .. api.playerController:GetFullName())
    end,
    buildSettings = function(api, panel)
        local value = api.get('enabled', true)
        local label = api.label(panel, value and 'Example enabled' or 'Example disabled', 18)
        api.button(panel, 'Toggle example', function()
            value = not value
            api.set('enabled', value)
            label:SetText(FText(value and 'Example enabled' or 'Example disabled'))
        end)
    end,
}
