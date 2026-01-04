import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { dashboardAPI, securityAPI } from '../api/services'
import {
  Radio,
  Wifi,
  WifiOff,
  AlertTriangle,
  Bell,
  Thermometer,
  Droplets,
  Sun,
  Battery,
  Shield,
  ShieldOff,
  RefreshCw
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

// Card component
function StatCard({ title, value, subtitle, icon: Icon, color = 'agri', link }) {
  const colorClasses = {
    agri: 'bg-agri-100 text-agri-600',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
  }

  const Card = (
    <div className="bg-white rounded-xl shadow-sm p-6 card-hover">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )

  if (link) {
    return <Link to={link}>{Card}</Link>
  }
  return Card
}

// Alert item component
function AlarmItem({ alarm }) {
  const priorityColors = {
    critical: 'border-l-red-500 bg-red-50',
    high: 'border-l-orange-500 bg-orange-50',
    medium: 'border-l-yellow-500 bg-yellow-50',
    low: 'border-l-blue-500 bg-blue-50',
  }

  const classificationLabels = {
    person: '🧑 Persona',
    tamper: '⚠️ Manomissione',
    animal_lg: '🦊 Animale grande',
    animal_sm: '🐈 Animale piccolo',
    unknown: '❓ Sconosciuto',
  }

  return (
    <div className={`border-l-4 p-4 rounded-r-lg ${priorityColors[alarm.priority] || priorityColors.medium}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium text-gray-900">
            {classificationLabels[alarm.classification] || alarm.classification}
          </p>
          <p className="text-sm text-gray-600">Nodo: {alarm.node_name || alarm.node}</p>
        </div>
        <span className="text-xs text-gray-500">
          {new Date(alarm.triggered_at).toLocaleTimeString('it-IT')}
        </span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [activeAlarms, setActiveAlarms] = useState([])
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = async () => {
    try {
      const [summaryRes, alarmsRes, chartsRes] = await Promise.all([
        dashboardAPI.getSummary(),
        securityAPI.getActiveAlarms(),
        dashboardAPI.getCharts(24)
      ])
      
      setSummary(summaryRes.data)
      setActiveAlarms(alarmsRes.data)
      
      // Formatta dati per il grafico
      if (chartsRes.data.sensor_data) {
        const formatted = chartsRes.data.sensor_data.map(item => ({
          time: new Date(item.hour).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
          temperatura: item.avg_temp ? parseFloat(item.avg_temp).toFixed(1) : null,
          umidità: item.avg_humidity ? parseFloat(item.avg_humidity).toFixed(0) : null,
          suolo: item.avg_soil ? parseFloat(item.avg_soil).toFixed(0) : null,
        }))
        setChartData(formatted)
      }
    } catch (error) {
      console.error('Errore caricamento dashboard:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Auto refresh ogni 60 secondi
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

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
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Panoramica del sistema AgriSecure</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Aggiorna
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Nodi Online"
          value={summary?.nodes_online || 0}
          subtitle={`su ${summary?.total_nodes || 0} totali`}
          icon={Wifi}
          color="green"
          link="/nodes"
        />
        <StatCard
          title="Nodi Offline"
          value={summary?.nodes_offline || 0}
          icon={WifiOff}
          color={summary?.nodes_offline > 0 ? 'red' : 'green'}
          link="/nodes"
        />
        <StatCard
          title="Allarmi Attivi"
          value={summary?.active_alarms || 0}
          subtitle={`${summary?.alarms_today || 0} oggi`}
          icon={Bell}
          color={summary?.active_alarms > 0 ? 'red' : 'green'}
          link="/alarms"
        />
        <StatCard
          title="Sistema"
          value={summary?.system_armed ? 'ARMATO' : 'DISARMATO'}
          subtitle={summary?.arm_mode || ''}
          icon={summary?.system_armed ? Shield : ShieldOff}
          color={summary?.system_armed ? 'green' : 'yellow'}
          link="/arm"
        />
      </div>

      {/* Sensori attuali */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Thermometer className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Temperatura</p>
              <p className="text-2xl font-bold text-gray-900">
                {summary?.latest_temperature ? `${parseFloat(summary.latest_temperature).toFixed(1)}°C` : '-'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Droplets className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Umidità</p>
              <p className="text-2xl font-bold text-gray-900">
                {summary?.latest_humidity ? `${parseFloat(summary.latest_humidity).toFixed(0)}%` : '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Sun className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Umidità Suolo</p>
              <p className="text-2xl font-bold text-gray-900">
                {summary?.latest_soil_moisture ? `${parseFloat(summary.latest_soil_moisture).toFixed(0)}%` : '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Grafico e Allarmi */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Grafico */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Andamento Ultime 24 Ore</h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="temperatura" stroke="#ef4444" name="Temp (°C)" dot={false} />
                <Line type="monotone" dataKey="umidità" stroke="#3b82f6" name="Umidità (%)" dot={false} />
                <Line type="monotone" dataKey="suolo" stroke="#f59e0b" name="Suolo (%)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-500">
              Nessun dato disponibile
            </div>
          )}
        </div>

        {/* Allarmi attivi */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Allarmi Attivi</h3>
            <Link to="/alarms" className="text-sm text-agri-600 hover:text-agri-700">
              Vedi tutti →
            </Link>
          </div>
          
          {activeAlarms.length > 0 ? (
            <div className="space-y-3">
              {activeAlarms.slice(0, 5).map((alarm) => (
                <AlarmItem key={alarm.id} alarm={alarm} />
              ))}
              {activeAlarms.length > 5 && (
                <p className="text-sm text-gray-500 text-center">
                  +{activeAlarms.length - 5} altri allarmi
                </p>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-gray-500">
              <Shield className="h-12 w-12 text-green-500 mb-2" />
              <p>Nessun allarme attivo</p>
            </div>
          )}
        </div>
      </div>

      {/* Avvisi batteria */}
      {summary?.battery_warnings > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center">
          <Battery className="h-6 w-6 text-yellow-600 mr-3" />
          <div>
            <p className="font-medium text-yellow-800">Attenzione Batterie</p>
            <p className="text-sm text-yellow-700">
              {summary.battery_warnings} {summary.battery_warnings === 1 ? 'nodo ha' : 'nodi hanno'} la batteria sotto il 20%
            </p>
          </div>
          <Link 
            to="/nodes" 
            className="ml-auto px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
          >
            Verifica
          </Link>
        </div>
      )}
    </div>
  )
}
