(function () {
    'use strict';

    const mapEl      = document.getElementById('geom-map');
    const hidden     = document.getElementById('id_geom_geojson');
    if (!mapEl || !hidden || typeof L === 'undefined') return;

    const geomType   = mapEl.dataset.geomType   || 'polygon';
    const entitySlug = mapEl.dataset.entity     || '';
    const parentField= mapEl.dataset.parentField|| '';
    const parentUrl  = mapEl.dataset.parentUrl  || '';
    const contextUrl = mapEl.dataset.contextUrl || '';

    // ─── Khởi tạo bản đồ ───
    const map = L.map(mapEl).setView([10.7936, 106.6661], 17);

    L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 22, maxNativeZoom: 17, attribution: 'Tiles &copy; Esri' }
    ).addTo(map);

    // ─── Lớp cha gợi ý (nét đứt xanh) ───
    const parentLayer = L.geoJSON(null, {
        style: { color: '#86efac', weight: 2, dashArray: '6 4', fillColor: '#bbf7d0', fillOpacity: 0.12 },
    }).addTo(map);

    // ─── Lớp vẽ chỉnh sửa ───
    const drawn = new L.FeatureGroup().addTo(map);

    // ─── Styles cho các lớp ngữ cảnh ───
    const CONTEXT_STYLES = {
        campus:   { color: '#0b3d2e', weight: 2.5, fillColor: '#16a34a', fillOpacity: 0.06, dashArray: null },
        campuses: { color: '#0b3d2e', weight: 2,   fillColor: '#16a34a', fillOpacity: 0.05, dashArray: '6 3' },
        building: { color: '#92400e', weight: 2,   fillColor: '#fbbf24', fillOpacity: 0.25 },
        buildings:{ color: '#92400e', weight: 1.5, fillColor: '#fbbf24', fillOpacity: 0.20 },
        floor:    { color: '#c2410c', weight: 2,   fillColor: '#fdba74', fillOpacity: 0.22 },
        floors:   { color: '#c2410c', weight: 1.5, fillColor: '#fdba74', fillOpacity: 0.18, dashArray: '4 3' },
        rooms:    { color: '#9d174d', weight: 1.5, fillColor: '#f9a8d4', fillOpacity: 0.35 },
        greens:   { color: '#15803d', weight: 1,   fillColor: '#4ade80', fillOpacity: 0.28 },
        parkings: { color: '#1e3a8a', weight: 1,   fillColor: '#93c5fd', fillOpacity: 0.28 },
    };

    const CONTEXT_LABELS = {
        campus:   'Khuôn viên',
        campuses: 'Khuôn viên hiện có',
        building: 'Tòa nhà',
        buildings:'Tòa nhà hiện có',
        floor:    'Tầng',
        floors:   'Tầng hiện có',
        rooms:    'Phòng hiện có',
        greens:   'Mảng xanh',
        parkings: 'Bãi xe',
        trees:    'Cây xanh',
    };

    // ─── Group chứa các lớp ngữ cảnh ───
    let ctxGroup = L.layerGroup().addTo(map);

    // ─── Helpers ───
    function getGeom(layer) { return JSON.stringify(layer.toGeoJSON().geometry); }
    function setValue(layer) { hidden.value = getGeom(layer); }

    function fitTo(lyr) {
        try {
            const b = lyr.getBounds ? lyr.getBounds() : null;
            if (b && b.isValid()) map.fitBounds(b, { padding: [32, 32], maxZoom: 19 });
        } catch (e) {}
    }

    function addExisting() {
        if (!hidden.value) return;
        try {
            const geo = JSON.parse(hidden.value);
            L.geoJSON(geo).eachLayer(function (l) {
                drawn.addLayer(l);
                setValue(l);
            });
            fitTo(drawn);
        } catch (e) {}
    }

    // ─── Load parent gợi ý (nét đứt) ───
    function loadParent(id) {
        if (!id || !parentUrl) return;
        const url = parentUrl.replace('/0/', '/' + id + '/');
        fetch(url)
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (geo) {
                parentLayer.clearLayers();
                if (!geo) return;
                parentLayer.addData(geo);
                if (!hidden.value && parentLayer.getBounds().isValid()) {
                    map.fitBounds(parentLayer.getBounds(), { padding: [32, 32], maxZoom: 19 });
                }
            })
            .catch(function () {});
    }

    // ─── Load context layers từ API ───
    function loadContext(params) {
        if (!contextUrl) return;
        const qs = Object.keys(params)
            .filter(function (k) { return params[k]; })
            .map(function (k) { return k + '=' + encodeURIComponent(params[k]); })
            .join('&');

        fetch(contextUrl + (qs ? '?' + qs : ''))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data) return;
                ctxGroup.clearLayers();

                Object.keys(data).forEach(function (key) {
                    const geojson = data[key];
                    if (!geojson || !geojson.features || !geojson.features.length) return;
                    const label = CONTEXT_LABELS[key] || key;

                    if (key === 'trees') {
                        L.geoJSON(geojson, {
                            pointToLayer: function (f, latlng) {
                                return L.circleMarker(latlng, {
                                    radius: 5, color: '#14532d', fillColor: '#22c55e',
                                    fillOpacity: 0.85, weight: 1,
                                });
                            },
                            onEachFeature: function (f, lyr) {
                                lyr.bindTooltip('🌳 ' + (f.properties.species || 'Cây xanh'));
                            },
                        }).addTo(ctxGroup);
                        return;
                    }

                    const style = CONTEXT_STYLES[key];
                    if (!style) return;

                    L.geoJSON(geojson, {
                        style: style,
                        onEachFeature: function (f, lyr) {
                            const name = f.properties.name || f.properties.species || '';
                            const lvl  = (f.properties.level !== undefined && f.properties.level !== null)
                                ? ' (Tầng ' + f.properties.level + ')' : '';
                            lyr.bindTooltip('<b>' + label + '</b><br>' + name + lvl);
                        },
                    }).addTo(ctxGroup);
                });
            })
            .catch(function () {});
    }

    // ─── Mapping entity → param key của select ───
    function getContextTrigger() {
        // Trả về { el: <selectElement>, key: 'campus'|'building'|'floor' }
        var e = entitySlug;
        if (e === 'toa-nha' || e === 'bai-xe' || e === 'mang-xanh' || e === 'cay-xanh') {
            var s = document.getElementById('id_campus');
            return s ? { el: s, key: 'campus' } : null;
        }
        if (e === 'tang') {
            var s = document.getElementById('id_building');
            return s ? { el: s, key: 'building' } : null;
        }
        if (e === 'phong') {
            var s = document.getElementById('id_floor');
            return s ? { el: s, key: 'floor' } : null;
        }
        if (e === 'co-so') {
            // Load tất cả cơ sở khi vào trang thêm cơ sở mới
            return { el: null, key: null };
        }
        return null;
    }

    // ─── Init ───
    addExisting();

    var trigger = getContextTrigger();

    // Load ngữ cảnh ngay khi vào trang.
    // Với entity 'phong': KHÔNG load ở đây vì cascade JS (entity_form.html) sẽ
    // dispatch 'change' lên id_floor sau khi AJAX cascade hoàn tất, tránh race condition.
    // Với các entity khác: load ngay nếu select đã có giá trị.
    setTimeout(function () {
        if (!trigger) return;
        if (entitySlug === 'phong') return;  // cascade sẽ tự dispatch change
        if (trigger.el && trigger.el.value) {
            var p = {}; p[trigger.key] = trigger.el.value;
            loadContext(p);
        } else if (!trigger.el && entitySlug === 'co-so') {
            loadContext({});
        }
    }, 150);

    // Lắng nghe thay đổi select → reload context
    if (trigger && trigger.el) {
        trigger.el.addEventListener('change', function () {
            ctxGroup.clearLayers();
            if (trigger.el.value) {
                var p = {}; p[trigger.key] = trigger.el.value;
                loadContext(p);
            }
        });
    }

    // ─── Vẽ hình học ───
    if (geomType === 'point') {
        map.on('click', function (e) {
            drawn.clearLayers();
            const marker = L.marker(e.latlng, { draggable: true }).addTo(drawn);
            setValue(marker);
            marker.on('dragend', function () { setValue(marker); });
        });
        drawn.eachLayer(function (layer) {
            if (layer.dragging) {
                layer.dragging.enable();
                layer.on('dragend', function () { setValue(layer); });
            }
        });
    } else if (typeof L.Control !== 'undefined' && L.Control.Draw) {
        const drawControl = new L.Control.Draw({
            draw: {
                polyline: false, circle: false, circlemarker: false, marker: false,
                rectangle: true,
                polygon: { allowIntersection: false, showArea: true },
            },
            edit: { featureGroup: drawn, remove: true },
        });
        map.addControl(drawControl);
        map.on(L.Draw.Event.CREATED, function (e) {
            drawn.clearLayers();
            drawn.addLayer(e.layer);
            setValue(e.layer);
        });
        map.on(L.Draw.Event.EDITED, function (e) {
            e.layers.eachLayer(function (l) { setValue(l); });
        });
        map.on(L.Draw.Event.DELETED, function () { hidden.value = ''; });
    }

    // ─── Parent gợi ý (nét đứt) ───
    if (parentField) {
        const sel = document.getElementById('id_' + parentField);
        if (sel) {
            sel.addEventListener('change', function () { loadParent(sel.value); });
            if (sel.value) loadParent(sel.value);
        }
    }

    setTimeout(function () { map.invalidateSize(); fitTo(drawn); }, 200);
})();
