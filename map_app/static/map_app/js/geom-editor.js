(function () {
    const mapEl = document.getElementById("geom-map");
    const hidden = document.getElementById("id_geom_geojson");
    if (!mapEl || !hidden || typeof L === "undefined") return;

    const geomType = mapEl.dataset.geomType || "polygon";
    const parentField = mapEl.dataset.parentField;
    const parentUrl = mapEl.dataset.parentUrl || "";
    const map = L.map(mapEl).setView([10.7936, 106.6661], 17);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 22,
        attribution: "© OpenStreetMap · HCMUNRE",
    }).addTo(map);

    const parentLayer = L.geoJSON(null, {
        style: {
            color: "#86efac",
            weight: 2,
            dashArray: "6 4",
            fillColor: "#bbf7d0",
            fillOpacity: 0.12,
        },
    }).addTo(map);

    const drawn = new L.FeatureGroup();
    map.addLayer(drawn);

    function geometryFromLayer(layer) {
        return JSON.stringify(layer.toGeoJSON().geometry);
    }

    function setValue(layer) {
        hidden.value = geometryFromLayer(layer);
    }

    function addExisting() {
        if (!hidden.value) return;
        try {
            const geo = JSON.parse(hidden.value);
            const layer = L.geoJSON(geo);
            layer.eachLayer(function (l) {
                drawn.addLayer(l);
                setValue(l);
            });
            fitDrawn();
        } catch (e) {}
    }

    function fitDrawn() {
        if (!drawn.getLayers().length) return;
        const bounds = drawn.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { maxZoom: 19, padding: [28, 28] });
        }
    }

    function loadParent(id) {
        if (!id || !parentUrl) return;
        const url = parentUrl.replace("/0/", "/" + id + "/");
        fetch(url)
            .then(function (res) { return res.ok ? res.json() : null; })
            .then(function (geo) {
                parentLayer.clearLayers();
                if (!geo) return;
                parentLayer.addData(geo);
                if (!hidden.value && parentLayer.getBounds().isValid()) {
                    map.fitBounds(parentLayer.getBounds(), { padding: [28, 28], maxZoom: 19 });
                }
            })
            .catch(function () {});
    }

    addExisting();

    if (geomType === "point") {
        map.on("click", function (e) {
            drawn.clearLayers();
            const marker = L.marker(e.latlng, { draggable: true }).addTo(drawn);
            setValue(marker);
            marker.on("dragend", function () { setValue(marker); });
        });
        drawn.eachLayer(function (layer) {
            if (layer.dragging) {
                layer.dragging.enable();
                layer.on("dragend", function () { setValue(layer); });
            }
        });
    } else if (typeof L.Control !== "undefined" && L.Control.Draw) {
        const drawControl = new L.Control.Draw({
            draw: {
                polyline: false,
                circle: false,
                circlemarker: false,
                marker: false,
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
            e.layers.eachLayer(function (layer) { setValue(layer); });
        });
        map.on(L.Draw.Event.DELETED, function () {
            hidden.value = "";
        });
    }

    if (parentField) {
        const select = document.getElementById("id_" + parentField);
        if (select) {
            select.addEventListener("change", function () {
                loadParent(select.value);
            });
            if (select.value) loadParent(select.value);
        }
    }

    window.setTimeout(function () {
        map.invalidateSize();
        fitDrawn();
    }, 200);
})();
