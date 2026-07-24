export interface FirmwareType {
  name: string
  key: string
}

export interface Device {
  id: string
  userId: string
  macAddress: string
  lastConnectedAtTimestamp: string | null
  autoUpdate: number
  board: string
  alias?: string
  agentId: string
  appVersion: string
  sort: number
  updater?: string
  updateDate: string
  creator: string
  createDate: string
}
