import { useEffect, useState } from 'react'
import './App.css'

const NAV = [['dashboard', 'Dashboard', '⌂'], ['calls', 'Call Center', '◌'], ['bookings', 'Bookings', '▣'], ['villages', 'Villages', '⌁'], ['supply', 'Supply Requests', '↗'], ['sms', 'SMS', '▱'], ['ivr', 'Demo IVR', '◉']]
const DEMO_BOOKINGS = [
  { id: 'BK-20260821-001', farmer: 'Demo Farmer', mobile: '9000000001', village: 'Demo Village', quantity: 4, store: 'Demo Village Cooperative Store', valid: '23 Aug 2026' },
  { id: 'BK-20260821-002', farmer: 'Test Farmer', mobile: '9000000002', village: 'Test Village', quantity: 6, store: 'Test Village Rythu Kendram', valid: '23 Aug 2026' },
]

function maskMobile(value) { return `${value.slice(0, 2)}••••••${value.slice(-2)}` }
function Badge({ children, tone = 'green' }) { return <span className={`badge ${tone}`}>{children}</span> }
function Metric({ label, value, detail, tone = '' }) { return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article> }
function Overline({ children }) { return <span className="overline">{children}</span> }
function Heading({ eyebrow, title, description, action }) { return <div className="view-heading"><div><Overline>{eyebrow}</Overline><h2>{title}</h2><p>{description}</p></div>{action}</div> }
function PanelTitle({ overline, title, action }) { return <div className="panel-title"><div><Overline>{overline}</Overline><h3>{title}</h3></div>{action}</div> }
function Empty({ title, text }) { return <div className="empty-state"><strong>{title}</strong><span>{text}</span></div> }

function App() {
  const [view, setView] = useState('dashboard')
  const [villages, setVillages] = useState([])
  const [loadingData, setLoadingData] = useState(true)
  const [mobile, setMobile] = useState('')
  const [otp, setOtp] = useState('')
  const [ivrStep, setIvrStep] = useState('mobile')
  const [farmer, setFarmer] = useState(null)
  const [booking, setBooking] = useState(null)
  const [ivrVillage, setIvrVillage] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function refreshVillages() {
    setLoadingData(true)
    try {
      const names = ['Demo Village', 'Test Village']
      const responses = await Promise.all(names.map((name) => fetch(`/village/${encodeURIComponent(name)}/stores`)))
      const data = await Promise.all(responses.map((response) => response.json()))
      setVillages(data.map((item, index) => ({ village: names[index], ...item })))
    } finally { setLoadingData(false) }
  }
  useEffect(() => { refreshVillages() }, [])

  const demand = villages.map((item) => item.demand).filter(Boolean)
  const active = demand.reduce((sum, item) => sum + item.total_active_bookings, 0)
  const booked = demand.reduce((sum, item) => sum + item.total_booked_urea, 0)
  const requests = demand.filter((item) => item.additional_urea_required > 0).length

  async function verifyOtp(event) {
    event.preventDefault(); setError('')
    if (!/^\d{10}$/.test(mobile)) return setError('Enter a valid 10-digit mobile number.')
    if (otp !== '123456') return setError('The demo OTP is 123456.')
    setBusy(true)
    try {
      const response = await fetch(`/farmer/${mobile}`); const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Farmer lookup failed.')
      const villageResponse = await fetch(`/village/${encodeURIComponent(data.village)}/stores`); const village = await villageResponse.json()
      if (!villageResponse.ok) throw new Error(village.detail || 'Village lookup failed.')
      setFarmer(data); setIvrVillage(village); setIvrStep('farmer')
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }
  async function bookUrea() {
    setBusy(true); setError('')
    try {
      const response = await fetch(`/booking/${mobile}`, { method: 'POST' }); const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Booking failed.')
      setBooking(data); setIvrVillage({ stores: data.village_stores, demand: data.village_demand }); setIvrStep('confirmed'); refreshVillages()
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }
  function resetIvr() { setMobile(''); setOtp(''); setIvrStep('mobile'); setFarmer(null); setIvrVillage(null); setBooking(null); setError('') }

  function IvrView() {
    return <><Heading eyebrow="DEMO IVR · FARMER CALL EXPERIENCE" title="Run a guided fertilizer booking" description="Use synthetic data to demonstrate the multilingual voice-assisted journey." action={<Badge tone="blue">Demo environment</Badge>} /><div className="ivr-layout"><section className="ivr-panel"><div className="stepper"><span>01</span><i /><span className={ivrStep !== 'mobile' ? 'on' : ''}>02</span><i /><span className={ivrStep === 'confirmed' ? 'on' : ''}>03</span></div>{ivrStep === 'mobile' && <form onSubmit={(event) => { event.preventDefault(); if (/^\d{10}$/.test(mobile)) setIvrStep('otp'); else setError('Enter a valid 10-digit mobile number.') }}><Overline>STEP 01 · IDENTIFY</Overline><h3>Enter a registered mobile number</h3><p className="muted">Retrieve farmer eligibility using the number registered in the demo.</p><label htmlFor="mobile">Mobile number</label><div className="phone-input"><span>+91</span><input id="mobile" value={mobile} onChange={(event) => setMobile(event.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="9000000001" /></div><button className="button primary-button" type="submit">Continue <b>→</b></button></form>}{ivrStep === 'otp' && <form onSubmit={verifyOtp}><Overline>STEP 02 · VERIFY</Overline><h3>Confirm the caller</h3><p className="muted">Demo verification code: <strong>123456</strong>. No real OTP service is used.</p><label htmlFor="otp">Verification code</label><input id="otp" className="otp-input" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="123456" autoFocus /><button className="button primary-button" type="submit" disabled={busy}>{busy ? 'Checking...' : 'Verify caller'} <b>→</b></button><button className="link-button" type="button" onClick={() => setIvrStep('mobile')}>← Change number</button></form>}{ivrStep === 'farmer' && farmer && <div><Overline>STEP 03 · ELIGIBILITY</Overline><h3>Caller verified: {farmer.name}</h3><p className="muted">{farmer.village} · {farmer.land_acres} acres · system eligibility</p><div className="entitlement"><span>Urea entitlement</span><strong>{farmer.urea_eligible_bags} bags</strong></div><button className="button primary-button" onClick={bookUrea} disabled={busy}>{busy ? 'Creating booking...' : 'Book eligible Urea'} <b>→</b></button></div>}{ivrStep === 'confirmed' && booking && <div><div className="confirmation-mark">✓</div><Overline>BOOKING CONFIRMED</Overline><h3>{booking.reserved ? `Reserved for ${booking.name}` : `Demand registered for ${booking.name}`}</h3><p className="muted">{booking.urea_bags} bags · {booking.store_name} · valid until {booking.valid_until}</p><div className="pickup-code"><span>Pickup code</span><strong>{booking.pickup_code}</strong></div><Badge tone={booking.reserved ? 'green' : 'amber'}>{booking.status}</Badge><button className="link-button" onClick={resetIvr}>Start another demo call</button></div>}{error && <p className="error-message">{error}</p>}</section><aside className="context-card"><Overline>OPERATIONS CONTEXT</Overline><h3>What the employee sees</h3><p className="muted">Eligibility is read from synthetic farmer data. Village stock is checked before a store is assigned.</p><div className="context-row"><span>Verification</span><Badge>OTP verified</Badge></div><div className="context-row"><span>Identity data</span><strong>Masked in tables</strong></div><div className="context-row"><span>SMS</span><strong>Simulated only</strong></div></aside></div></>
  }

  function Dashboard() { return <><Heading eyebrow="OPERATIONS OVERVIEW · 21 AUG 2026" title="Good morning, operations team" description="Monitor farmer access, village stock, and supply readiness from one place." action={<button className="button secondary-button" onClick={refreshVillages}>↻ Refresh data</button>} /><section className="metrics"><Metric label="Total calls today" value="24" detail="+8% vs yesterday" /><Metric label="Successful bookings" value={active || '—'} detail="Verified farmer journeys" tone="accent" /><Metric label="Active bookings" value={active || '—'} detail={`${booked} Urea bags requested`} /><Metric label="Pending supply requests" value={requests} detail="Villages needing stock" tone={requests ? 'warning' : ''} /><Metric label="SMS sent" value={active || '—'} detail="Simulated confirmations" /><Metric label="Expired bookings" value="2" detail="Released back to stock" /></section><div className="two-columns"><section className="table-panel"><PanelTitle overline="NETWORK HEALTH" title="Village demand" action={<Badge tone="blue">Live demo data</Badge>} /><DemandTable villages={villages} loading={loadingData} /></section><section className="table-panel"><PanelTitle overline="LIVE QUEUE" title="Recent calls" action={<button className="quiet-button" onClick={() => setView('calls')}>View all</button>} /><CallsTable /></section></div><section className="table-panel"><PanelTitle overline="BOOKING OPERATIONS" title="Recent bookings" action={<button className="quiet-button" onClick={() => setView('bookings')}>View all</button>} /><BookingsTable /></section></> }
  function Villages() { return <><Heading eyebrow="NETWORK · VILLAGE OPERATIONS" title="Village details" description="Stock and demand visibility by local supply network." /> <div className="village-cards">{villages.map((item) => <VillageCard key={item.village} item={item} />)}</div></> }
  function Supply() { const open = villages.filter((item) => item.demand?.additional_urea_required > 0); return <><Heading eyebrow="LOGISTICS · ACTION REQUIRED" title="Supply requests" description="Villages where active demand is ahead of available stock." /><section className="table-panel">{open.length ? open.map((item) => <div className="supply-request" key={item.village}><div><Overline>VILLAGE SUPPLY REQUIRED</Overline><h3>{item.village}</h3><p>{item.demand.additional_urea_required} additional bags required for {item.demand.total_active_bookings} active bookings.</p></div><Badge tone="amber">OPEN</Badge></div>) : <Empty title="No open supply requests" text="All tracked villages currently have enough stock for active demand." />}</section></> }
  function OtherView({ title, eyebrow, description, children }) { return <><Heading eyebrow={eyebrow} title={title} description={description} />{children}</> }
  const content = view === 'dashboard' ? <Dashboard /> : view === 'ivr' ? <IvrView /> : view === 'villages' ? <Villages /> : view === 'supply' ? <Supply /> : view === 'calls' ? <OtherView eyebrow="VOICE ACCESS" title="Call center queue" description="Review verified calls and assisted farmer journeys."><section className="table-panel"><CallsTable detailed /></section></OtherView> : view === 'bookings' ? <OtherView eyebrow="BOOKING OPERATIONS" title="Bookings" description="Track active reservations and village demand."><section className="table-panel"><BookingsTable detailed /></section></OtherView> : <OtherView eyebrow="COMMUNICATIONS" title="SMS center" description="Synthetic confirmation activity for the demo network."><section className="table-panel"><Empty title="Simulated SMS notifications" text="SMS content is generated by the backend and marked as simulated. No message is sent." /></section></OtherView>

  return <div className="product-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">KC</div><div><strong>Kisan Connect</strong><span>Fertilizer access network</span></div></div><span className="nav-label">WORKSPACE</span><nav>{NAV.map(([id, label, icon]) => <button key={id} className={`nav-item ${view === id ? 'active' : ''}`} onClick={() => setView(id)}><span className="nav-icon">{icon}</span>{label}{id === 'supply' && requests > 0 && <b>{requests}</b>}</button>)}</nav><div className="sidebar-footer"><span className="online"><i />Demo network online</span><p>Multilingual Voice-Based<br />Fertilizer Access & Village<br />Supply Network</p></div></aside><main className="main-content"><header className="main-header"><div className="mobile-brand"><span className="brand-mark">KC</span><strong>Kisan Connect</strong></div><span className="sync-status">● Last sync just now</span><button className="avatar">OP</button></header><div className="content-wrap">{content}</div></main></div>
}

function DemandTable({ villages, loading }) { if (loading) return <div className="loading-state">Loading village network…</div>; return <div className="table-scroll"><table><thead><tr><th>Village</th><th>Total stock</th><th>Active</th><th>Booked Urea</th><th>Available</th><th>Additional</th><th>Status</th></tr></thead><tbody>{villages.map((item) => <tr key={item.village}><td><strong>{item.village}</strong></td><td>{item.demand?.total_village_stock ?? 0} bags</td><td>{item.demand?.total_active_bookings ?? 0}</td><td>{item.demand?.total_booked_urea ?? 0} bags</td><td>{item.demand?.current_village_stock ?? 0} bags</td><td>{item.demand?.additional_urea_required ?? 0} bags</td><td><Badge tone={item.demand?.additional_urea_required ? 'amber' : 'green'}>{item.demand?.additional_urea_required ? 'SUPPLY REQUIRED' : 'STOCK AVAILABLE'}</Badge></td></tr>)}</tbody></table></div> }
function CallsTable({ detailed = false }) { const calls = [['10:42', '90••••••01', 'Telugu', 'Verified', 'Booking created'], ['10:18', '90••••••02', 'English', 'Verified', 'Eligibility found'], ['09:56', '91••••••44', 'Hindi', 'Pending', 'Callback queued'], ['09:21', '88••••••72', 'Telugu', 'Verified', 'Stock inquiry']]; return <div className="table-scroll"><table><thead><tr><th>Time</th><th>Masked mobile</th><th>Language</th><th>Verification</th><th>Result</th></tr></thead><tbody>{calls.slice(0, detailed ? 4 : 3).map((call) => <tr key={call[0]}><td>{call[0]}</td><td><strong>{call[1]}</strong></td><td>{call[2]}</td><td><Badge tone={call[3] === 'Verified' ? 'green' : 'amber'}>{call[3]}</Badge></td><td>{call[4]}</td></tr>)}</tbody></table></div> }
function BookingsTable({ detailed = false }) { return <div className="table-scroll"><table><thead><tr><th>Booking ID</th><th>Farmer</th><th>Masked mobile</th><th>Village</th><th>Urea</th><th>Pickup store</th><th>Valid until</th><th>Status</th><th>SMS</th></tr></thead><tbody>{DEMO_BOOKINGS.slice(0, detailed ? 2 : 2).map((item) => <tr key={item.id}><td><strong>{item.id}</strong></td><td>{item.farmer}</td><td>{maskMobile(item.mobile)}</td><td>{item.village}</td><td>{item.quantity} bags</td><td>{item.store}</td><td>{item.valid}</td><td><Badge>{item.status}</Badge></td><td><Badge tone="blue">Simulated</Badge></td></tr>)}</tbody></table></div> }
function VillageCard({ item }) { return <article className="village-card"><PanelTitle overline="VILLAGE NETWORK" title={item.village} action={<Badge tone={item.demand?.additional_urea_required ? 'amber' : 'green'}>{item.demand?.additional_urea_required ? 'Supply required' : 'Stock available'}</Badge>} /><div className="village-metrics"><div><span>Village stock</span><strong>{item.demand?.total_village_stock ?? 0} bags</strong></div><div><span>Active bookings</span><strong>{item.demand?.total_active_bookings ?? 0}</strong></div><div><span>Total demand</span><strong>{item.demand?.total_booked_urea ?? 0} bags</strong></div><div><span>Available stock</span><strong>{item.demand?.current_village_stock ?? 0} bags</strong></div><div><span>Additional required</span><strong>{item.demand?.additional_urea_required ?? 0} bags</strong></div></div><h4>Village stores</h4>{(item.stores || []).map((store) => <div className="store-row" key={store.store_id}><div><strong>{store.name}</strong><small>{store.store_type}</small></div><b>{store.urea_stock} bags</b></div>)}</article> }

export default App
