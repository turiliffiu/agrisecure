import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  Settings as SettingsIcon,
  Bell,
  Moon,
  Sun,
  Globe,
  Save,
  RefreshCw,
  Server,
  Database,
  Wifi
} from 'lucide-react'

function SettingSection({ title, description, children }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
      {children}
    </div>
  )
}

function ToggleSetting({ label, description, enabled, onChange }) {
  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-agri-600' : 'bg-gray-200'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}

export default function Settings() {
  const { user, logout } = useAuth()
  const [settings, setSettings] = useState({
    notifications: {
      push: true,
      email: true,
      telegram: true,
      sms: false,
      soundAlerts: true,
    },
    display: {
      darkMode: false,
      compactView: false,
      autoRefresh: true,
      refreshInterval: 60,
    },
  })
  const [saving, setSaving] = useState(false)

  const updateSetting = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    // Simula salvataggio
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaving(false)
    alert('Impostazioni salvate!')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Impostazioni</h1>
        <p className="text-gray-500">Configura le preferenze del sistema</p>
      </div>

      {/* Notifications */}
      <SettingSection
        title="Notifiche"
        description="Gestisci come ricevere gli alert"
      >
        <div className="divide-y">
          <ToggleSetting
            label="Notifiche Push"
            description="Ricevi notifiche nel browser"
            enabled={settings.notifications.push}
            onChange={(v) => updateSetting('notifications', 'push', v)}
          />
          <ToggleSetting
            label="Email"
            description="Ricevi alert via email"
            enabled={settings.notifications.email}
            onChange={(v) => updateSetting('notifications', 'email', v)}
          />
          <ToggleSetting
            label="Telegram"
            description="Ricevi messaggi sul bot Telegram"
            enabled={settings.notifications.telegram}
            onChange={(v) => updateSetting('notifications', 'telegram', v)}
          />
          <ToggleSetting
            label="SMS"
            description="Ricevi SMS per allarmi critici (costa)"
            enabled={settings.notifications.sms}
            onChange={(v) => updateSetting('notifications', 'sms', v)}
          />
          <ToggleSetting
            label="Suoni Alert"
            description="Riproduci suono per nuovi allarmi"
            enabled={settings.notifications.soundAlerts}
            onChange={(v) => updateSetting('notifications', 'soundAlerts', v)}
          />
        </div>
      </SettingSection>

      {/* Display */}
      <SettingSection
        title="Visualizzazione"
        description="Personalizza l'aspetto della dashboard"
      >
        <div className="divide-y">
          <ToggleSetting
            label="Modalità Scura"
            description="Tema scuro per ridurre l'affaticamento visivo"
            enabled={settings.display.darkMode}
            onChange={(v) => updateSetting('display', 'darkMode', v)}
          />
          <ToggleSetting
            label="Vista Compatta"
            description="Mostra più informazioni in meno spazio"
            enabled={settings.display.compactView}
            onChange={(v) => updateSetting('display', 'compactView', v)}
          />
          <ToggleSetting
            label="Aggiornamento Automatico"
            description="Ricarica i dati automaticamente"
            enabled={settings.display.autoRefresh}
            onChange={(v) => updateSetting('display', 'autoRefresh', v)}
          />
          {settings.display.autoRefresh && (
            <div className="py-3">
              <label className="block font-medium text-gray-900 mb-2">
                Intervallo aggiornamento
              </label>
              <select
                value={settings.display.refreshInterval}
                onChange={(e) => updateSetting('display', 'refreshInterval', Number(e.target.value))}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
              >
                <option value={30}>30 secondi</option>
                <option value={60}>1 minuto</option>
                <option value={120}>2 minuti</option>
                <option value={300}>5 minuti</option>
              </select>
            </div>
          )}
        </div>
      </SettingSection>

      {/* System Info */}
      <SettingSection
        title="Informazioni Sistema"
        description="Stato del backend e connessioni"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center p-4 bg-green-50 rounded-lg">
            <Server className="h-5 w-5 text-green-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500">Backend</p>
              <p className="font-medium text-green-700">Online</p>
            </div>
          </div>
          <div className="flex items-center p-4 bg-green-50 rounded-lg">
            <Database className="h-5 w-5 text-green-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500">Database</p>
              <p className="font-medium text-green-700">Connesso</p>
            </div>
          </div>
          <div className="flex items-center p-4 bg-green-50 rounded-lg">
            <Wifi className="h-5 w-5 text-green-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500">MQTT Broker</p>
              <p className="font-medium text-green-700">Attivo</p>
            </div>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t">
          <p className="text-sm text-gray-500">
            <strong>Versione:</strong> 1.0.0
          </p>
          <p className="text-sm text-gray-500">
            <strong>API URL:</strong> {window.location.origin}/api/v1/
          </p>
        </div>
      </SettingSection>

      {/* Account */}
      <SettingSection
        title="Account"
        description="Gestisci il tuo account"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Utente</p>
              <p className="text-sm text-gray-500">{user?.username || 'admin'}</p>
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              Esci
            </button>
          </div>
        </div>
      </SettingSection>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center px-6 py-3 bg-agri-600 text-white font-medium rounded-lg hover:bg-agri-700 disabled:opacity-50"
        >
          {saving ? (
            <>
              <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
              Salvataggio...
            </>
          ) : (
            <>
              <Save className="h-5 w-5 mr-2" />
              Salva Impostazioni
            </>
          )}
        </button>
      </div>
    </div>
  )
}
