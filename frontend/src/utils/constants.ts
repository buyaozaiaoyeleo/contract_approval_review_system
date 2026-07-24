export const TOKEN_KEY = 'contract_review_token'
export const REFRESH_TOKEN_KEY = 'contract_review_refresh_token'
export const USER_INFO_KEY = 'contract_review_user_info'

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
export const DEFAULT_PAGE_SIZE = 20

export const DATE_FORMAT = 'YYYY-MM-DD'
export const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

export const FILE_SIZE_LIMIT = 50 * 1024 * 1024

export const POLLING_INTERVAL = 5000

export const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws/tasks`