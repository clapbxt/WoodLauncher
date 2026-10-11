local package = {}

local magic = 'TUNG-MOD/1\n'
local limits = {metadata=8192, source=1024*1024, icon=4*1024*1024}
local field_limits = {id=40, name=80, version=40, author=60, description=500}

local function read_line(file, label)
    local line = file:read('*l')
    if not line or not line:match('^%d+$') then
        error('Invalid TUNG mod package ' .. label .. ' length.')
    end
    local length = tonumber(line)
    if not length or length < 0 or length > limits[label] then
        error('TUNG mod package ' .. label .. ' is too large.')
    end
    return length
end

local function parse_metadata(text)
    local metadata = {}
    local count = 0
    for line in text:gmatch('[^\n]+') do
        local key, value = line:match('^([%w_]+)=(.*)$')
        if not key or metadata[key] ~= nil then error('Invalid TUNG mod package metadata.') end
        if not field_limits[key] or #value > field_limits[key] then
            error('TUNG mod package metadata contains an unsupported or oversized field.')
        end
        metadata[key] = value
        count = count + 1
    end
    if count ~= 5 then error('TUNG mod package metadata must contain exactly five fields.') end
    for _, key in ipairs({'id', 'name', 'version', 'author', 'description'}) do
        if not metadata[key] or metadata[key] == '' then
            error('TUNG mod package is missing metadata: ' .. key)
        end
    end
    if not metadata.id:match('^[a-z0-9][a-z0-9_-]*$') then
        error('TUNG mod package has an unsafe mod ID.')
    end
    return metadata
end

local function valid_png(icon)
    if #icon == 0 then return true end
    if icon:sub(1, 8) ~= '\137PNG\r\n\026\n' or #icon < 24 then return false end
    if icon:byte(9) ~= 0 or icon:byte(10) ~= 0 or icon:byte(11) ~= 0 or icon:byte(12) ~= 13 then
        return false
    end
    if icon:sub(13, 16) ~= 'IHDR' then return false end
    local function uint32(offset)
        local a, b, c, d = icon:byte(offset, offset + 3)
        return ((a * 256 + b) * 256 + c) * 256 + d
    end
    local width, height = uint32(17), uint32(21)
    return width > 0 and height > 0 and width <= 2048 and height <= 2048
        and width * height <= 4*1024*1024
end

function package.read(path, icon_path, loaded_ids)
    local file, err = io.open(path, 'rb')
    if not file then error('Could not open TUNG mod package: ' .. tostring(err)) end
    local size = file:seek('end')
    if not size or size > limits.metadata + limits.source + limits.icon + 128 then
        file:close()
        error('TUNG mod package exceeds the maximum file size.')
    end
    file:seek('set', 0)
    local result = table.pack(pcall(function()
        if file:read(#magic) ~= magic then error('Unsupported TUNG mod package format.') end
        local metadata_length = read_line(file, 'metadata')
        local source_length = read_line(file, 'source')
        local icon_length = read_line(file, 'icon')
        local metadata_bytes = file:read(metadata_length)
        local source = file:read(source_length)
        local icon = icon_length == 0 and '' or file:read(icon_length)
        if not metadata_bytes or #metadata_bytes ~= metadata_length
            or not source or #source ~= source_length or not icon or #icon ~= icon_length then
            error('TUNG mod package is truncated.')
        end
        if file:read(1) ~= nil then error('TUNG mod package has trailing data.') end
        if #source == 0 then error('TUNG mod package contains an empty Lua source.') end
        if not valid_png(icon) then error('TUNG mod package contains an invalid or oversized PNG icon.') end
        local metadata = parse_metadata(metadata_bytes)
        if loaded_ids and loaded_ids[metadata.id] then
            error('Duplicate mod ID: ' .. metadata.id)
        end
        local extracted_icon
        if #icon > 0 then
            extracted_icon = icon_path .. metadata.id .. '.png'
            local output, write_error = io.open(extracted_icon, 'wb')
            if not output then error('Could not write packaged mod icon: ' .. tostring(write_error)) end
            local wrote, write_error = output:write(icon)
            if not wrote then output:close(); error(tostring(write_error)) end
            output:close()
        end
        return metadata, source, extracted_icon
    end))
    file:close()
    if not result[1] then error(result[2]) end
    return table.unpack(result, 2, result.n)
end

return package
