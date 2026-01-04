import { useState, useEffect } from 'react'
import { sensorsAPI, nodesAPI } from '../api/services'
import {
  Thermometer,
  Droplets,
  Sun,
  Wind,
  Gauge,
  AlertTriangle,
  CheckCircle,
  RefreshCw
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

function SensorCard({ title, value, unit, icon: Icon, color, trend }) {
  const colorClasses = {
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    amber: 'bg-amber-100 text-amber-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className={`text-sm ${trend > 0 ? 'text-red-500' : 'text-blue-500'}`}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}
          </span>
        )}
      </div>
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-3xl font-bold text-gray-900">
        {value !== null && value !== undefined ? value : '-'}
        <span className="text-lg font-normal text-gray-500 ml-1">{unit}</span>
      </p>
    </div>
  )
}

function AlertItem({ alert, onAcknowledge, onResolve }) {
  const severityColors = {
    critical: 'border-l-red-500 bg-red-50',
    warning: 'border-l-yellow-500 bg-yellow-50',
    info: 'border-l-blue-500 bg-blue-50',
  }

  return (
    <div className={`border-l-4 p-4 rounded-r-lg ${severityColors[alert.severity] || severityColors.warning}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium text-gray-900">{alert.alert_type}</p>
          <p className="text-sm text-gray-600">{alert.message}</p>
          <p className="text-xs text-gray-500 mt-1">
            {new Date(alert.created_at).toLocaleString('it-IT')}
          </p>
        </div>
        <div className="flex space-x-2">
          {!alert.is_acknowledged && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="text-sm px-3 py-1 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
            >
              ACK
            </button>
          )}
          {!alert.is_resolved && (
            <button
              onClick={() => onResolve(alert.id)}
              className="text-sm px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
            >
              Risolvi
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Sensors() {
  const [latestReadings, setLatestReadings] = useState({})
  const [chartData, setChartData] = useState([])
  const [alerts, setAlerts] = useState([])
  const [nodes, setNodes] = useState([])
  const [selectedNode, setSelectedNode] = useState('all')
  const [timeRange, setTimeRange] = useState(24)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchData()
  }, [selectedNode, timeRange])

  const fetchData = async () => {
    try {
      const [latestRes, alertsRes, nodesRes] = await Promise.all([
        sensorsAPI.getLatest(),
        sensorsAPI.getAlerts({ is_resolved: false }),
        nodesAPI.getAll()
      ])

      // Processa le ultime letture
      const readings = latestRes.data.results || latestRes.data
      if (Array.isArray(readings) && readings.length > 0) {
        // Prendi le ultime letture aggregate
        const latest = readings[0]
        setLatestReadings({
          temperature: latest.temperature,
          humidity: latest.humidity,
          pressure: latest.pressure,
          light: latest.light,
          soil_moisture: latest.soil_moisture,
        })
      }

      setAlerts(alertsRes.data.results || alertsRes.data)
      setNodes((nodesRes.data.results || nodesRes.data).filter(n => n.node_type === 'ambient'))

      // Carica dati grafico
      await fetchChartData()
    } catch (error) {
      console.error('Errore caricamento sensori:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const fetchChartData = async () => {
    try {
      const params = { hours: timeRange, limit: 200 }
      if (selectedNode !== 'all') {
        params.node_id = selectedNode
      }
      const response = await sensorsAPI.getReadings(params)
      const readings = response.data.results || response.data

      // Aggrega per ora
      const hourlyData = {}
      readings.forEach(reading => {
        const hour = new Date(reading.timestamp).toISOString().slice(0, 13)
        if (!hourlyData[hour]) {
          hourlyData[hour] = { temps: [], hums: [], soils: [] }
        }
        if (reading.temperature) hourlyData[hour].temps.push(reading.temperature)
        if (reading.humidity) hourlyData[hour].hums.push(reading.humidity)
        if (reading.soil_moisture) hourlyData[hour].soils.push(reading.soil_moisture)
      })

      const formatted = Object.entries(hourlyData).map(([hour, data]) => ({
        time: new Date(hour).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
        temperatura: data.temps.length ? (data.temps.reduce((a, b) => a + b, 0) / data.temps.length).toFixed(1) : null,
        umidità: data.hums.length ? (data.hums.reduce((a, b) => a + b, 0) / data.hums.length).toFixed(0) : null,
        suolo: data.soils.length ? (data.soils.reduce((a, b) => a + b, 0) / data.soils.length).toFixed(0) : null,
      })).sort((a, b) => a.time.localeCompare(b.time))

      setChartData(formatted)
    } catch (error) {
      console.error('Errore caricamento grafico:', error)
    }
  }

  const handleAcknowledge = async (alertId) => {
    try {
      await sensorsAPI.acknowledgeAlert(alertId)
      fetchData()
    } catch (error) {
      console.error('Errore acknowledge:', error)
    }
  }

  const handleResolve = async (alertId) => {
    try {
      await sensorsAPI.resolveAlert(alertId)
      fetchData()
    } catch (error) {
      console.error('Errore resolve:', error)
    }
  }

  const handleRefresh = () => {
    setRefreshing(true)
    fetchData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-agri-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sensori</h1>
          <p className="text-gray-500">Monitoraggio ambientale in tempo reale</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Aggiorna
        </button>
      </div>

      {/* Sensor Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <SensorCard
          title="Temperatura"
          value={latestReadings.temperature?.toFixed(1)}
          unit="°C"
          icon={Thermometer}
          color="red"
        />
        <SensorCard
          title="Umidità Aria"
          value={latestReadings.humidity?.toFixed(0)}
          unit="%"
          icon={Droplets}
          color="blue"
        />
        <SensorCard
          title="Pressione"
          value={latestReadings.pressure?.toFixed(0)}
          unit="hPa"
          icon={Gauge}
          color="purple"
        />
        <SensorCard
          title="Luminosità"
          value={latestReadings.light?.toFixed(0)}
          unit="lux"
          icon={Sun}
          color="amber"
        />
        <SensorCard
          title="Umidità Suolo"
          value={latestReadings.soil_moisture?.toFixed(0)}
          unit="%"
          icon={Wind}
          color="green"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 flex flex-wrap gap-4">
        <select
          value={selectedNode}
          onChange={(e) => setSelectedNode(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
        >
          <option value="all">Tutti i nodi</option>
          {nodes.map(node => (
            <option key={node.id} value={node.node_id}>
              {node.name || node.node_id}
            </option>
          ))}
        </select>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(Number(e.target.value))}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
        >
          <option value={6}>Ultime 6 ore</option>
          <option value={12}>Ultime 12 ore</option>
          <option value={24}>Ultime 24 ore</option>
          <option value={48}>Ultime 48 ore</option>
          <option value={168}>Ultima settimana</option>
        </select>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Andamento Temporale</h3>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="temperatura" stroke="#ef4444" name="Temperatura (°C)" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="umidità" stroke="#3b82f6" name="Umidità (%)" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="suolo" stroke="#22c55e" name="Suolo (%)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Nessun dato disponibile per il periodo selezionato
          </div>
        )}
      </div>

      {/* Alerts */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Alert Attivi</h3>
          <span className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-600">
            {alerts.length} alert
          </span>
        </div>
        
        {alerts.length > 0 ? (
          <div className="space-y-3">
            {alerts.map(alert => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <CheckCircle className="h-12 w-12 text-green-500 mb-2" />
            <p>Nessun alert attivo</p>
          </div>
        )}
      </div>
    </div>
  )
}
