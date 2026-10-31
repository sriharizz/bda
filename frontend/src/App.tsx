import { useState, useMemo } from 'react';
import { 
  Activity, 
  MapPin, 
  Flame, 
  Trees, 
  AlertTriangle, 
  Database, 
  Cpu, 
  Layers, 
  X, 
  ChevronRight, 
  Clock
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer 
} from 'recharts';

import { MapComponent, type Station } from './components/MapComponent';

// Import exported analytics data
import allStationsRaw from './data/stations.json';
import citySummariesRaw from './data/city_summaries.json';
import diurnalTrendsRaw from './data/diurnal_trends.json';
import spikesRecentRaw from './data/spikes_recent.json';
import bigdataMetaRaw from './data/bigdata_meta.json';

const allStations = allStationsRaw as Station[];
const citySummaries = citySummariesRaw as Record<string, any>;
const diurnalTrends = diurnalTrendsRaw as Record<string, any[]>;
const spikesRecent = spikesRecentRaw as any[];
const bigdataMeta = bigdataMetaRaw;

const METRO_SHORTCUTS = [
  { name: 'Bengaluru', label: '🌳 Bengaluru', center: [12.9716, 77.5946] as [number, number], zoom: 11.8 },
  { name: 'Delhi', label: '🔥 Delhi NCR', center: [28.6139, 77.2090] as [number, number], zoom: 11.2 },
  { name: 'Mumbai', label: '🌊 Mumbai', center: [19.0760, 72.8777] as [number, number], zoom: 11.5 },
  { name: 'Hyderabad', label: '💎 Hyderabad', center: [17.3850, 78.4867] as [number, number], zoom: 11.5 },
  { name: 'Kolkata', label: '🎭 Kolkata', center: [22.5726, 88.3639] as [number, number], zoom: 11.5 },
  { name: 'Pune', label: '🏔️ Pune', center: [18.5204, 73.8567] as [number, number], zoom: 11.5 }
];

export function App() {
  const [selectedCity, setSelectedCity] = useState<string>('Bengaluru');
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [showZones, setShowZones] = useState<boolean>(true);
  const [showSparkModal, setShowSparkModal] = useState<boolean>(false);
  const [filterTaxonomy, setFilterTaxonomy] = useState<string>('ALL');

  // Detect coordinates for current selected city
  const cityStations = useMemo(() => {
    return allStations.filter(s => s.city_name.toLowerCase() === selectedCity.toLowerCase());
  }, [selectedCity]);

  // City center
  const mapCenter = useMemo<[number, number]>(() => {
    if (cityStations.length > 0) {
      const avgLat = cityStations.reduce((acc, s) => acc + s.latitude, 0) / cityStations.length;
      const avgLon = cityStations.reduce((acc, s) => acc + s.longitude, 0) / cityStations.length;
      return [avgLat, avgLon];
    }
    const shortcut = METRO_SHORTCUTS.find(m => m.name.toLowerCase() === selectedCity.toLowerCase());
    return shortcut ? shortcut.center : [20.5937, 78.9629];
  }, [selectedCity, cityStations]);

  const mapZoom = useMemo(() => {
    return selectedCity === 'ALL' ? 4.5 : 11.6;
  }, [selectedCity]);

  // Filtered stations for map based on pill filter (Strict 1:1 Taxonomic Alignment)
  const displayedStations = useMemo(() => {
    let list = cityStations.length > 0 ? cityStations : allStations;
    if (filterTaxonomy === 'CLEAN') {
      list = list.filter(s => s.classification.includes('Compliant'));
    } else if (filterTaxonomy === 'HOTSPOT') {
      list = list.filter(s => s.classification.includes('Persistent'));
    } else if (filterTaxonomy === 'SPIKE') {
      list = list.filter(s => s.classification.includes('Occasional'));
    }
    return list;
  }, [cityStations, filterTaxonomy]);

  // Current city metrics
  const currentSummary = citySummaries[selectedCity] || {
    city: selectedCity,
    station_count: cityStations.length,
    mean_pm25: cityStations.length > 0 ? (cityStations.reduce((a, b) => a + b.mean_pm25, 0) / cityStations.length).toFixed(1) : 0,
    cleanest_station: cityStations.length > 0 ? cityStations.sort((a,b)=>a.mean_pm25-b.mean_pm25)[0] : null,
    worst_station: cityStations.length > 0 ? cityStations.sort((a,b)=>b.mean_pm25-a.mean_pm25)[0] : null,
  };

  // Diurnal data for chart
  const diurnalData = diurnalTrends[selectedCity] || diurnalTrends['Bengaluru'] || [];

  const allCityNames = useMemo(() => {
    return Object.keys(citySummaries).sort();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#070a12] text-slate-100 font-sans overflow-hidden">
      
      {/* Top Executive Header */}
      <header className="h-16 px-6 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-xl flex items-center justify-between shrink-0 z-30">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Activity className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">AirPulse India</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Spark 3.5 & HDFS
              </span>
            </div>
            <p className="text-xs text-slate-400">Distributed Air Pollution Spike & Hotspot Intelligence Platform</p>
          </div>
        </div>

        {/* Quick Metro Switcher */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
          {METRO_SHORTCUTS.map(metro => (
            <button
              key={metro.name}
              onClick={() => {
                setSelectedCity(metro.name);
                setSelectedStation(null);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedCity.toLowerCase() === metro.name.toLowerCase()
                  ? 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-md shadow-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {metro.label}
            </button>
          ))}
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center gap-3">
          {/* City Search Dropdown */}
          <div className="relative">
            <select
              value={selectedCity}
              onChange={(e) => {
                setSelectedCity(e.target.value);
                setSelectedStation(null);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-sky-500 appearance-none cursor-pointer"
            >
              {allCityNames.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <ChevronRight className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 rotate-90 pointer-events-none" />
          </div>

          <button
            onClick={() => setShowZones(!showZones)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border transition-all ${
              showZones 
                ? 'bg-sky-500/10 text-sky-400 border-sky-500/30' 
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Toggle Soft Dispersion Zones"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Zones</span>
          </button>

          <button
            onClick={() => setShowSparkModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-all shadow-sm"
          >
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Spark & HDFS Proof</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden p-4 gap-4">
        
        {/* Left Column: Interactive Map & Bottom Stats Ribbon (62%) */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          
          {/* Map Card Header with Filter Pills */}
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-sky-400" />
                <span>{selectedCity} Station Radar</span>
              </span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400 font-medium">
                {displayedStations.length} of {cityStations.length || allStations.length} Sensors Active
              </span>
            </div>

            {/* Micro Filter Pills */}
            <div className="flex items-center gap-1.5 text-xs">
              <button
                onClick={() => setFilterTaxonomy('ALL')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all ${
                  filterTaxonomy === 'ALL'
                    ? 'bg-slate-700 text-white border-slate-600'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterTaxonomy('CLEAN')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border flex items-center gap-1 transition-all ${
                  filterTaxonomy === 'CLEAN'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-emerald-400'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                Clean (≤30)
              </button>
              <button
                onClick={() => setFilterTaxonomy('HOTSPOT')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border flex items-center gap-1 transition-all ${
                  filterTaxonomy === 'HOTSPOT'
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-rose-400'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                Chronic Hotspots
              </button>
              <button
                onClick={() => setFilterTaxonomy('SPIKE')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border flex items-center gap-1 transition-all ${
                  filterTaxonomy === 'SPIKE'
                    ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-orange-400'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
                Episodic Spikes
              </button>
            </div>
          </div>

          {/* Map Canvas */}
          <div className="flex-1 relative min-h-0">
            {displayedStations.length === 0 && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[500] bg-slate-900/95 backdrop-blur-md px-4 py-3 rounded-xl border border-slate-700 shadow-2xl flex items-center gap-3 text-xs text-slate-200 max-w-lg">
                <div className="w-2 h-2 rounded-full bg-amber-400 shrink-0"></div>
                <div>
                  {filterTaxonomy === 'SPIKE' && selectedCity === 'Delhi' ? (
                    <span>All 38 stations in Delhi are classified as <b>Chronic Persistent Hotspots</b> due to severe daily exceedance (0 purely episodic spike zones). Check cities like <b>Pune</b> or <b>Chennai</b> to see active episodic spikes!</span>
                  ) : filterTaxonomy === 'HOTSPOT' && selectedCity === 'Bengaluru' ? (
                    <span>All stations in Bengaluru are currently <b>Compliant / Moderate</b> (0 chronic hotspots). Check <b>Delhi NCR</b> to view 38 chronic hotspots!</span>
                  ) : (
                    <span>No stations match the <b>{filterTaxonomy}</b> filter in {selectedCity}.</span>
                  )}
                </div>
                <button 
                  onClick={() => setFilterTaxonomy('ALL')}
                  className="ml-auto text-sky-400 hover:text-sky-300 font-bold whitespace-nowrap text-[11px] px-2 py-1 bg-slate-800 rounded"
                >
                  Show All
                </button>
              </div>
            )}

            <MapComponent
              stations={displayedStations}
              selectedStation={selectedStation}
              onSelectStation={(s) => setSelectedStation(s)}
              userLocation={{ lat: 12.9716, lon: 77.5946, city: 'Bengaluru' }}
              center={mapCenter}
              zoom={mapZoom}
              showZones={showZones}
            />

            {/* Map Legend Overlay at Bottom-Left */}
            <div className="absolute bottom-4 left-4 z-[500] bg-slate-900/90 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-800 shadow-xl flex items-center gap-4 text-xs font-medium">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span className="text-slate-300">Clean Air</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <span className="text-slate-300">Moderate Traffic</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
                <span className="text-slate-300">Spike Zone</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span className="text-slate-300">Chronic Hotspot</span>
              </div>
              <div className="flex items-center gap-1.5 pl-2 border-l border-slate-700">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500 ring-2 ring-white"></span>
                <span className="text-sky-300">Your Position</span>
              </div>
            </div>
          </div>

          {/* Bottom Execution Evidence Ribbon */}
          <div className="h-12 bg-slate-900/80 rounded-xl border border-slate-800/80 px-4 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 font-medium text-slate-300">
                <Database className="w-3.5 h-3.5 text-sky-400" />
                <span>11.98M Curated Rows</span>
              </div>
              <span className="text-slate-700">|</span>
              <div>558 Indian Stations</div>
              <span className="text-slate-700">|</span>
              <div>151 Chronic Sinks Identified</div>
              <span className="text-slate-700">|</span>
              <div>66 Episodic Spike Zones</div>
            </div>

            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span className="text-emerald-400 font-semibold">PySpark Pipeline Live</span>
            </div>
          </div>
        </div>

        {/* Right Column: Executive Intelligence Console (38%) */}
        <div className="w-[430px] shrink-0 flex flex-col gap-3 overflow-y-auto pr-1">
          
          {/* Card 1: City Overview & Compliance */}
          <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 shadow-xl">
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Metropolitan Assessment</span>
                <h2 className="text-xl font-extrabold text-white">{selectedCity}</h2>
              </div>
              <div className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                Number(currentSummary.mean_pm25) <= 60 
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}>
                {Number(currentSummary.mean_pm25) <= 60 ? '✓ WITHIN NAAQS SAFE LIMIT' : '🚨 EXCEEDS NAAQS SAFE LIMIT'}
              </div>
            </div>

            {/* City PM2.5 Metric Bar */}
            <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800/80 mb-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-semibold">City Average PM2.5</div>
                <div className="text-2xl font-black text-white">
                  {currentSummary.mean_pm25} <span className="text-xs font-normal text-slate-400">µg/m³</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Statutory Standard</div>
                <div className="text-sm font-bold text-slate-300">60 µg/m³ <span className="text-[10px] text-slate-500">(CPCB 24h)</span></div>
              </div>
            </div>

            {/* Cleanest vs Worst Station Micro Comparison */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-xl p-2.5">
                <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 uppercase">
                  <Trees className="w-3 h-3" />
                  <span>Cleanest Pocket</span>
                </div>
                <div className="font-bold text-slate-100 truncate mt-1">
                  {currentSummary.cleanest_station?.name || 'N/A'}
                </div>
                <div className="text-emerald-400 font-extrabold text-sm mt-0.5">
                  {currentSummary.cleanest_station?.mean_pm25} µg/m³
                </div>
              </div>

              <div className="bg-rose-950/20 border border-rose-900/50 rounded-xl p-2.5">
                <div className="flex items-center gap-1 text-[10px] font-bold text-rose-400 uppercase">
                  <Flame className="w-3 h-3" />
                  <span>Peak Hotspot</span>
                </div>
                <div className="font-bold text-slate-100 truncate mt-1">
                  {currentSummary.worst_station?.name || 'N/A'}
                </div>
                <div className="text-rose-400 font-extrabold text-sm mt-0.5">
                  {currentSummary.worst_station?.mean_pm25} µg/m³
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Selected Station Drill-down (If clicked) */}
          {selectedStation ? (
            <div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-2xl border border-sky-500/40 p-4 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-sky-500/10 rounded-full blur-2xl pointer-events-none"></div>
              
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-1.5 text-[10px] font-bold text-sky-400 uppercase tracking-wider">
                    <MapPin className="w-3 h-3" />
                    <span>Selected Station Inspector</span>
                  </div>
                  <h3 className="text-base font-bold text-white mt-0.5">{selectedStation.station_name}</h3>
                </div>
                <button
                  onClick={() => setSelectedStation(null)}
                  className="text-slate-500 hover:text-slate-300 p-1 rounded-lg hover:bg-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800">
                  <div className="text-[10px] text-slate-400">Mean PM2.5</div>
                  <div className="text-lg font-bold text-sky-400">{Math.round(selectedStation.mean_pm25)}</div>
                  <div className="text-[9px] text-slate-500">µg/m³</div>
                </div>
                <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800">
                  <div className="text-[10px] text-slate-400">Days Exceeded</div>
                  <div className="text-lg font-bold text-rose-400">{selectedStation.chronic_exceedance_pct}%</div>
                  <div className="text-[9px] text-slate-500">&gt;60 µg/m³</div>
                </div>
                <div className="bg-slate-900/90 rounded-lg p-2 border border-slate-800">
                  <div className="text-[10px] text-slate-400">Volatility (P95/P50)</div>
                  <div className="text-lg font-bold text-amber-400">{selectedStation.volatility_ratio}</div>
                  <div className="text-[9px] text-slate-500">Spike Ratio</div>
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-400">Taxonomic Class:</span>
                <span className="font-semibold text-slate-200">{selectedStation.classification}</span>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 rounded-xl border border-dashed border-slate-800 p-3 text-center text-xs text-slate-500">
              💡 Tip: Click any glowing pill on the map to inspect that station's micro-history.
            </div>
          )}

          {/* Card 3: 24-Hour Diurnal Rush-Hour Patterns */}
          <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">24-Hour Diurnal Rush Cycles</span>
              </div>
              <span className="text-[10px] text-slate-400 font-semibold">{selectedCity} Typical Day</span>
            </div>

            <p className="text-[11px] text-slate-400 mb-3">
              Peaks at <b className="text-slate-200">08:00 - 10:00 (Traffic)</b> and <b className="text-slate-200">21:00 - 00:00 (Inversion)</b>.
            </p>

            {diurnalData.length > 0 ? (
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={diurnalData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id="pm25Gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0}/>
                      </linearGradient>
                      <linearGradient id="pm10Gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="hour" stroke="#475569" fontSize={9} tickLine={false} interval={3} />
                    <YAxis stroke="#475569" fontSize={9} tickLine={false} />
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                    />
                    <Area type="monotone" dataKey="pm10" stroke="#38bdf8" strokeWidth={2} fillOpacity={1} fill="url(#pm10Gradient)" name="PM10" />
                    <Area type="monotone" dataKey="pm25" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#pm25Gradient)" name="PM2.5" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-32 flex items-center justify-center text-xs text-slate-500">
                Diurnal data aggregated in Spark SQL mart
              </div>
            )}
          </div>

          {/* Card 4: Explainable Anomaly Spike Radar */}
          <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">Explainable Anomaly Radar</span>
              </div>
              <span className="text-[10px] text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                Rolling MAD (M_i ≥ 3.5)
              </span>
            </div>

            <p className="text-[11px] text-slate-400 mb-2">
              Boris Iglewicz & Hoaglin Modified Z-Score isolates acute surges departing from baseline:
            </p>

            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 text-xs">
              {spikesRecent.slice(0, 4).map((spike, idx) => (
                <div key={idx} className="bg-slate-950/70 p-2 rounded-xl border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-slate-200 truncate max-w-[210px]">{spike.station_name}</div>
                    <div className="text-[10px] text-slate-500">{spike.city_name} • {spike.date}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-bold text-rose-400">{Math.round(spike.daily_pm25)} µg/m³</div>
                    <div className="text-[10px] text-slate-400">{spike.spike_ratio}x baseline</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Spark SQL & HDFS Verification Modal (High Z-Index above Leaflet panes) */}
      {showSparkModal && (
        <div className="fixed inset-0 z-[9999] bg-black/85 backdrop-blur-md flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden relative z-[10000]">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-base">Hadoop HDFS & Apache Spark Execution Proof</h3>
              </div>
              <button
                onClick={() => setShowSparkModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs font-mono">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-bold mb-1">// Distributed Lakehouse Storage Architecture</div>
                <div className="text-emerald-400">Storage Backend: {bigdataMeta.storage_backend}</div>
                <div className="text-sky-400">Compute Engine: {bigdataMeta.compute_engine}</div>
                <div className="text-slate-300">Total Measurements Ingested: 11,988,849 rows</div>
                <div className="text-slate-300">Hive Partitions: {bigdataMeta.curated_partitions}</div>
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-bold mb-1">// Enforced Sensor Cleaning Invariants (PySpark)</div>
                {bigdataMeta.invariants_enforced.map((inv: string, i: number) => (
                  <div key={i} className="text-indigo-300">✓ {inv}</div>
                ))}
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-bold mb-1">// Actual Spark SQL Physical Query Execution Plan</div>
                <pre className="text-slate-400 whitespace-pre-wrap text-[11px] max-h-56 overflow-y-auto">
                  {bigdataMeta.execution_plan_snippet}
                </pre>
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end">
              <button
                onClick={() => setShowSparkModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-lg text-xs"
              >
                Close Verification
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
export default App;
