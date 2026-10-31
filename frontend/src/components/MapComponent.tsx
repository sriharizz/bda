import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export interface Station {
  station_id: string;
  station_name: string;
  short_name: string;
  city_name: string;
  state_name: string;
  latitude: number;
  longitude: number;
  mean_pm25: number;
  chronic_exceedance_pct: number;
  volatility_ratio: number;
  detected_spikes: number;
  classification: string;
  color_code: string;
}

interface MapProps {
  stations: Station[];
  selectedStation: Station | null;
  onSelectStation: (station: Station) => void;
  userLocation: { lat: number; lon: number; city: string };
  center: [number, number];
  zoom: number;
  showZones: boolean;
}

export const MapComponent: React.FC<MapProps> = ({
  stations,
  selectedStation,
  onSelectStation,
  userLocation,
  center,
  zoom,
  showZones
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const zonesLayerRef = useRef<L.LayerGroup | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: center,
      zoom: zoom,
      zoomControl: false,
      attributionControl: false
    });

    // High-resolution Dark Canvas layer (100% Free, NO API Key needed!)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
      subdomains: ['server', 'services'],
      attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
    }).addTo(map);

    // Clean roads, boundaries and street label overlay
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16
    }).addTo(map);

    // Zoom control at bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Attribution at bottom left
    L.control.attribution({ position: 'bottomleft', prefix: false })
      .addAttribution('&copy; Esri &copy; OpenStreetMap contributors')
      .addTo(map);

    const zonesLayer = L.layerGroup().addTo(map);
    const markersLayer = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;
    zonesLayerRef.current = zonesLayer;
    markersLayerRef.current = markersLayer;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update center & zoom smoothly
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    mapInstanceRef.current.flyTo(center, zoom, {
      duration: 1.2,
      easeLinearity: 0.25
    });
  }, [center, zoom]);

  // Update markers and zones
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current || !zonesLayerRef.current) return;

    markersLayerRef.current.clearLayers();
    zonesLayerRef.current.clearLayers();

    // 1. Draw User Location Beacon
    if (userLocation.lat && userLocation.lon) {
      const userIcon = L.divIcon({
        className: 'user-beacon-wrapper',
        html: `
          <div class="user-beacon" title="Your Location: ${userLocation.city}">
            <div class="pulse-ring"></div>
            <div class="center-dot"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      L.marker([userLocation.lat, userLocation.lon], { icon: userIcon })
        .bindTooltip(`📍 You Are Here (${userLocation.city})`, {
          direction: 'top',
          offset: [0, -10],
          className: 'bg-slate-900 text-sky-400 border border-slate-700 text-xs px-2 py-1 rounded shadow-lg'
        })
        .addTo(markersLayerRef.current);
    }

    // 2. Draw Stations
    stations.forEach(station => {
      const isSelected = selectedStation?.station_id === station.station_id;
      
      // Strict 1:1 color mapping based on taxonomic classification
      let dotColor = '#22c55e'; // Green: Compliant / Low Exposure
      if (station.classification.includes('Persistent')) {
        dotColor = '#ef4444'; // Red: Persistent Hotspot (Chronic Sink)
      } else if (station.classification.includes('Occasional')) {
        dotColor = '#f97316'; // Orange: Occasional Spike Zone (Episodic)
      } else if (station.classification.includes('Moderate')) {
        dotColor = '#eab308'; // Yellow/Amber: Moderate Hotspot
      }

      // Draw subtle zone dispersion halo
      if (showZones) {
        L.circle([station.latitude, station.longitude], {
          radius: 2000,
          fillColor: dotColor,
          fillOpacity: isSelected ? 0.22 : 0.08,
          color: dotColor,
          opacity: isSelected ? 0.7 : 0.3,
          weight: isSelected ? 2 : 1,
          dashArray: isSelected ? undefined : '3, 5'
        }).addTo(zonesLayerRef.current!);
      }

      // Clean compact pill marker (Compact by default, expands on select/hover)
      const pillHtml = isSelected
        ? `<div class="station-pill active">
             <span class="marker-dot" style="background-color: ${dotColor}"></span>
             <span class="name text-slate-100">${station.short_name}</span>
             <span class="marker-val" style="color: ${dotColor}">${Math.round(station.mean_pm25)}</span>
           </div>`
        : `<div class="station-pill">
             <span class="marker-dot" style="background-color: ${dotColor}"></span>
             <span class="marker-val" style="color: ${dotColor}">${Math.round(station.mean_pm25)}</span>
           </div>`;

      const pillIcon = L.divIcon({
        className: 'custom-station-marker',
        html: pillHtml,
        iconSize: isSelected ? [130, 26] : [44, 24],
        iconAnchor: isSelected ? [65, 13] : [22, 12]
      });

      const marker = L.marker([station.latitude, station.longitude], {
        icon: pillIcon,
        zIndexOffset: isSelected ? 1000 : 0
      });

      // Rich tooltip on hover
      marker.bindTooltip(`
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 2px;">${station.station_name}</div>
        <div style="color: #cbd5e1;">Mean PM2.5: <b style="color: ${dotColor}">${station.mean_pm25.toFixed(1)} µg/m³</b></div>
        <div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">${station.classification} (${station.chronic_exceedance_pct}% exceedance)</div>
      `, {
        direction: 'top',
        offset: [0, -10],
        className: 'station-tooltip'
      });

      marker.on('click', () => {
        onSelectStation(station);
      });

      marker.addTo(markersLayerRef.current!);
    });
  }, [stations, selectedStation, showZones, userLocation]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden border border-slate-800 shadow-2xl">
      <div ref={mapContainerRef} className="w-full h-full" />
    </div>
  );
};
