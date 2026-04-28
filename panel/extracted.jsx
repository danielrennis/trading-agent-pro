
        const { useState, useEffect } = React;

        function App() {
            const [status, setStatus] = useState({ positions: {} });
            const [config, setConfig] = useState({ strategy: {}, symbols: [] });
            const [pendingRotation, setPendingRotation] = useState(null);
            const [countdown, setCountdown] = useState(0);
            const [editConfig, setEditConfig] = useState(null);
            const [newSymbol, setNewSymbol] = useState("");

            const fetchStatus = async () => {
                const res = await fetch('/api/status');
                const data = await res.json();
                setStatus(data);
            };

            const fetchConfig = async () => {
                const res = await fetch('/api/config');
                const data = await res.json();
                setConfig(data);
                setEditConfig(data);
            };

            const saveConfig = async () => {
                await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(editConfig)
                });
                fetchConfig();
                alert("Configuración guardada. El orquestador se sincronizará en el próximo ciclo.");
            };

            const restartAgent = async () => {
                const ok = confirm("¿Estás seguro de que querés reiniciar el orquestador?");
                if (!ok) return;
                const res = await fetch('/api/restart', { method: 'POST' });
                const data = await res.json();
                alert(data.message);
            };

            const addSymbol = () => {
                if (!newSymbol) return;
                const sym = newSymbol.trim().toUpperCase();
                if (editConfig.watchlist.includes(sym)) {
                    setNewSymbol("");
                    return;
                }
                setEditConfig({
                    ...editConfig,
                    watchlist: [...editConfig.watchlist, sym]
                });
                setNewSymbol("");
            };

            const removeSymbol = (sym) => {
                setEditConfig({
                    ...editConfig,
                    watchlist: editConfig.watchlist.filter(s => s !== sym)
                });
            };

            const executeRotation = async (current, target) => {
                setPendingRotation(null);
                setCountdown(0);
                const res = await fetch(`/api/rotate?current_symbol=${current}&target_symbol=${target}`, { method: 'POST' });
                const data = await res.json();
                alert(data.message);
                fetchStatus();
            };

            const startRotationFlow = (currentSymbol) => {
                // Combinar oportunidades escaneadas con el resto de la watchlist
                const scannedSymbols = Object.keys(status.opportunities || {});
                const allWatchlist = config.watchlist || [];
                
                // Crear una lista completa de opciones
                const options = allWatchlist.map(sym => {
                    const data = (status.opportunities || {})[sym];
                    return [sym, data || { score: 0, price: "Pendiente" }];
                });

                // Ordenar: primero las que tienen score alto, luego el resto
                options.sort((a, b) => (b[1].score || 0) - (a[1].score || 0));
                
                if (options.length === 0) {
                    alert("Agregá símbolos a tu Watchlist para poder rotar.");
                    return;
                }

                setPendingRotation({
                    current: currentSymbol,
                    target: options[0][0],
                    options: options
                });
                setCountdown(60);
            };

            useEffect(() => {
                let timer;
                if (countdown > 0) {
                    timer = setInterval(() => {
                        setCountdown(prev => {
                            if (prev <= 1) {
                                executeRotation(pendingRotation.current, pendingRotation.target);
                                return 0;
                            }
                            return prev - 1;
                        });
                    }, 1000);
                }
                return () => clearInterval(timer);
            }, [countdown, pendingRotation]);

            useEffect(() => {
                fetchStatus();
                fetchConfig();
                const interval = setInterval(fetchStatus, 5000);
                return () => clearInterval(interval);
            }, []);

            const unrealizedProfit = Object.values(status.positions || {}).reduce((acc, pos) => {
                const price = pos.current_price || pos.entry_price;
                const multiplier = pos.multiplier || 1;
                return acc + ((price - pos.entry_price) * pos.qty * multiplier);
            }, 0);

            const realizedProfit = (status.history || []).reduce((acc, h) => acc + (h.profit_amount || 0), 0);

            return (
                <div className="max-w-7xl mx-auto p-8">
                    <div className="flex justify-between items-center mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-blue-400">Trading Bot Dashboard</h1>
                            <p className="text-gray-500 text-sm">Control Panel para CEDEARs y ONs</p>
                        </div>
                        <div className="flex items-center gap-4">
                            <button 
                                onClick={restartAgent}
                                className="bg-red-600/20 text-red-400 border border-red-600/30 px-4 py-2 rounded text-sm font-bold hover:bg-red-600/30 transition"
                            >
                                🔄 Reiniciar Agente
                            </button>
                            <div className="text-sm text-gray-400 bg-slate-800 px-3 py-2 rounded border border-slate-700">
                                Status: <span className="text-green-500 font-bold">Online</span>
                            </div>
                        </div>
                    </div>

                    {/* ACCOUNT METRICS */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                        <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 text-center">Disponible en Cuenta</div>
                            <div className="text-2xl font-bold font-mono text-white text-center">
                                ${Math.round(status.balance || 0).toLocaleString()}
                            </div>
                        </div>
                        <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 text-center">Sugerido p/ Invertir</div>
                            <div className="text-2xl font-bold font-mono text-blue-400 text-center">
                                ${Math.round((status.balance || 0) * (config.strategy.risk_balance_pct || 0)).toLocaleString()}
                            </div>
                        </div>
                        <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 text-center">Profit Cartera (Hoy)</div>
                            <div className={`text-2xl font-bold font-mono text-center ${unrealizedProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                ${unrealizedProfit >= 0 ? '+' : ''}
                                ${Math.round(unrealizedProfit).toLocaleString()}
                            </div>
                        </div>
                        <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 text-center">Profit Total Histórico</div>
                            <div className={`text-2xl font-bold font-mono text-center ${realizedProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {realizedProfit >= 0 ? '+' : ''}
                                ${Math.round(realizedProfit).toLocaleString()}
                            </div>
                        </div>
                    </div>
                    
                    <div className="space-y-8">
                        {/* Panel de Posiciones y Oportunidades */}
                            
                            {/* POSICIONES ACTIVAS (APAISADAS) */}
                            <section>
                                <h2 className="text-xl font-bold mb-4 flex items-center">
                                    <span className="mr-2">📊</span> Mi Cartera Real
                                </h2>
                                <div className="flex flex-col gap-4">
                                    {!status.positions || Object.keys(status.positions).length === 0 ? (
                                        <div className="bg-slate-800/50 p-12 rounded-xl border border-slate-700 text-center text-gray-400 italic">
                                            No hay posiciones abiertas actualmente.
                                        </div>
                                    ) : (
                                        Object.entries(status.positions).map(([symbol, pos]) => {
                                            // Calculate days held
                                            const buyDate = new Date(pos.buy_time || new Date());
                                            const daysHeld = Math.floor((new Date() - buyDate) / (1000 * 60 * 60 * 24));
                                            const currentPrice = pos.current_price || pos.entry_price;
                                            const profitPct = pos.profit_pct || 0;
                                            const multiplier = pos.multiplier || 1;
                                            const profitAmt = (currentPrice - pos.entry_price) * pos.qty * multiplier;
                                            const isWin = profitPct >= 0;
                                            
                                            // Range calculations
                                            const range = (pos.tp || currentPrice) - (pos.sl || currentPrice);
                                            const pct = range > 0 ? ((currentPrice - pos.sl) / range) * 100 : 50;
                                            const clampedPct = Math.min(Math.max(pct, 0), 100);

                                            return (
                                                <div key={symbol} className="bg-slate-800 p-4 rounded-xl border border-slate-700 hover:border-blue-500/50 transition relative overflow-hidden flex flex-col md:flex-row items-stretch justify-between gap-6">
                                                    <div className={`absolute top-0 left-0 h-full w-1 ${isWin ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                                    
                                                    {/* Symbol & Meta & Action */}
                                                    <div className="w-full md:w-2/12 pl-4 flex flex-col justify-between">
                                                        <div className="py-1">
                                                            <h2 className="text-3xl font-bold leading-none mb-1">{symbol}</h2>
                                                            <div className="text-xs text-gray-400 font-medium flex gap-2">
                                                                <span>{pos.qty} u. • {daysHeld}d</span>
                                                            </div>
                                                            <div className="text-sm font-bold text-gray-300 mt-1">
                                                                ${Math.round(currentPrice * pos.qty * multiplier).toLocaleString()}
                                                            </div>
                                                        </div>
                                                        <button 
                                                            onClick={() => startRotationFlow(symbol)}
                                                            className="text-[11px] bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 px-3 py-2 rounded-lg font-bold hover:bg-yellow-500/30 transition flex items-center justify-center gap-2 uppercase tracking-widest shadow-lg shadow-yellow-500/5"
                                                        >
                                                            <span>🔄</span> Rotar Posición
                                                        </button>
                                                                                           {/* Merged Price & Risk Column */}
                                                    <div className="w-full md:w-7/12 border-l border-slate-700 px-8 flex flex-col justify-between py-2">
                                                        {/* Top Part: Standard Prices - Left Aligned */}
                                                        <div className="flex justify-start items-start gap-8 w-full">
                                                            <div>
                                                                <div className="text-gray-500 text-[10px] uppercase font-medium leading-none mb-1">Compra</div>
                                                                <div className="font-mono text-white text-base font-bold leading-none">${Math.round(pos.entry_price).toLocaleString()}</div>
                                                            </div>
                                                            <div className="pt-2">
                                                                <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm ${isWin ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
                                                                    {isWin ? '▲' : '▼'} {Math.abs(profitPct).toFixed(1)}%
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className="text-gray-500 text-[10px] uppercase font-medium leading-none mb-1">Último</div>
                                                                <div className="font-mono text-white text-base font-bold leading-none">${Math.round(currentPrice).toLocaleString()}</div>
                                                            </div>
                                                        </div>

                                                        {/* Bottom Part: Range Visualizer */}
                                                        <div className="w-full mt-4">
                                                            <div className="flex justify-between items-end mb-1">
                                                                <div className="text-left">
                                                                    <div className="text-gray-500 text-[10px] uppercase font-medium mb-1">Piso (SL)</div>
                                                                    <div className="font-mono text-red-400 text-2xl font-bold leading-none">${Math.round(pos.sl || 0).toLocaleString()}</div>
                                                                </div>
                                                                
                                                                <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest pb-1">
                                                                    Rango de Estrategia
                                                                </div>

                                                                <div className="text-right">
                                                                    <div className="text-gray-500 text-[10px] uppercase font-medium mb-1">Techo (TP)</div>
                                                                    <div className="font-mono text-green-400 text-2xl font-bold leading-none">${Math.round(pos.tp || 0).toLocaleString()}</div>
                                                                </div>
                                                            </div>

                                                            {/* The Range Bar */}
                                                            <div className="relative h-1.5 bg-slate-700/50 rounded-full w-full mt-3">
                                                                {/* Progress track between SL and TP */}
                                                                <div className="absolute inset-0 bg-gradient-to-r from-red-500/20 via-slate-700/0 to-green-500/20 rounded-full"></div>
                                                                
                                                                {/* Current Price Pointer */}
                                                                <div 
                                                                    className="absolute top-1/2 -translate-y-1/2 transition-all duration-1000 ease-in-out"
                                                                    style={{ left: `${clampedPct}%` }}
                                                                >
                                                                    <div className="w-1 h-4 bg-blue-400 rounded-full shadow-[0_0_8px_rgba(96,165,250,0.5)]"></div>
                                                                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 text-[9px] font-bold text-blue-400 whitespace-nowrap bg-slate-900 px-1 rounded">
                                                                        ${Math.round(currentPrice).toLocaleString()}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Profit Metrics Only */}
                                                    <div className="w-full md:w-3/12 border-l border-slate-700 flex flex-col justify-between text-right pl-6 pr-4">
                                                        <div className="flex-1 flex flex-col justify-center">
                                                            <div className="text-gray-500 text-[10px] uppercase font-medium mb-1 leading-none">Profit Total</div>
                                                            <div className={`text-2xl font-bold leading-none ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                                                                ${Math.round(profitAmt).toLocaleString()}
                                                            </div>
                                                            <div className={`text-xs font-bold mt-1 ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                                                                {isWin ? '+' : ''}{profitPct.toFixed(2)}%
                                                            </div>
                                                        </div>
                                                        
                                                        {pos.daily_var !== undefined ? (
                                                            <div className="border-t border-slate-700/50 pt-2 mt-2 flex justify-between items-end">
                                                                <div className="text-xs font-bold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">
                                                                    ESC #{pos.step}
                                                                </div>
                                                                <div>
                                                                    <div className="text-gray-500 text-[10px] uppercase font-medium mb-1">Variación Hoy</div>
                                                                    <div className={`text-xl font-bold leading-none ${pos.daily_var >= 0 ? 'text-blue-400' : 'text-orange-400'}`}>
                                                                        ${Math.round( (currentPrice - (currentPrice / (1 + pos.daily_var/100))) * pos.qty * multiplier).toLocaleString()}
                                                                    </div>
                                                                    <div className={`text-[11px] font-bold mt-1 ${pos.daily_var >= 0 ? 'text-blue-400' : 'text-orange-400'}`}>
                                                                        {pos.daily_var >= 0 ? '+' : ''}{pos.daily_var.toFixed(2)}%
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="pt-2 mt-2 opacity-0 select-none">Placeholder</div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </section>

                            {/* MODAL DE ROTACIÓN */}
                            {pendingRotation && (
                                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
                                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-2xl max-w-md w-full shadow-2xl">
                                        <h3 className="text-xl font-bold mb-4 text-center">Configurar Rotación</h3>
                                        <p className="text-gray-400 text-sm mb-6 text-center">
                                            Vender <span className="text-white font-bold">{pendingRotation.current}</span> y rotar hacia:
                                        </p>
                                        <div className="space-y-3 mb-6 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                            {pendingRotation.options.map(([sym, opt]) => (
                                                <button 
                                                    key={sym}
                                                    onClick={() => setPendingRotation({...pendingRotation, target: sym})}
                                                    className={`w-full p-4 rounded-xl border flex justify-between items-center transition ${
                                                        pendingRotation.target === sym 
                                                        ? 'bg-blue-600/20 border-blue-500' 
                                                        : 'bg-slate-800 border-slate-700 hover:border-slate-500'
                                                    }`}
                                                >
                                                    <div className="text-left">
                                                        <div className="font-bold">{sym}</div>
                                                        <div className="text-[10px] text-gray-400">
                                                            {opt.score > 0 ? `Score: ${opt.score.toFixed(1)}` : 'Sin análisis previo'}
                                                        </div>
                                                    </div>
                                                    <div className="font-mono text-sm">
                                                        {typeof opt.price === 'number' ? `$${opt.price.toFixed(2)}` : opt.price}
                                                    </div>
                                                </button>
                                            ))}
                                         </div>
                                         <div className="bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-lg mb-6 flex justify-between items-center">
                                            <div className="text-left">
                                                <div className="text-yellow-500 font-bold text-lg leading-none">{countdown}s</div>
                                                <div className="text-[10px] text-yellow-500/80 uppercase">Autoejecución</div>
                                            </div>
                                            <button 
                                                onClick={() => setCountdown(0)}
                                                className="bg-yellow-500 text-black text-[10px] font-bold px-3 py-1 rounded-full uppercase hover:bg-yellow-400 transition"
                                            >
                                                🛑 Pausar
                                            </button>
                                         </div>
                                         <div className="flex gap-4">
                                             <button 
                                                 onClick={() => { setPendingRotation(null); setCountdown(0); }}
                                                 className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl font-bold transition text-sm"
                                             >
                                                 Cancelar
                                             </button>
                                             <button 
                                                 onClick={() => executeRotation(pendingRotation.current, pendingRotation.target)}
                                                 className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-xl font-bold transition text-sm"
                                             >
                                                 Rotar YA
                                             </button>
                                         </div>
                                    </div>
                                </div>
                            )}
                            
                            <section>
                                <h2 className="text-xl font-bold mb-4 flex items-center">
                                    <span className="mr-2">🚀</span> Oportunidades del Mercado (Watchlist)
                                </h2>
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                    {!status.opportunities ? (
                                        <div className="col-span-full text-gray-500 italic">Escaneando mercado...</div>
                                    ) : (
                                        <>
                                            {Object.entries(status.opportunities).map(([symbol, opt]) => (
                                                <div key={symbol} className="bg-slate-800/40 p-4 rounded-lg border border-slate-700 text-center relative overflow-hidden">
                                                    <div className="font-bold text-lg">{symbol}</div>
                                                    <div className={`text-xs font-bold my-1 ${opt.score >= 7.5 ? 'text-green-400' : 'text-gray-400'}`}>
                                                        Score: {opt.score.toFixed(1)}
                                                    </div>
                                                    <div className="text-[10px] text-gray-500">${opt.price}</div>
                                                    {opt.score >= 8.0 && (
                                                        <div className="mt-2 text-[9px] bg-green-500 text-black font-bold py-1 rounded animate-pulse">
                                                            RALLY DETECTADO
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                            {config.watchlist && config.watchlist
                                                .filter(sym => !status.opportunities[sym])
                                                .map(sym => (
                                                    <div key={sym} className="bg-slate-800/20 p-4 rounded-lg border border-slate-700/50 text-center opacity-50">
                                                        <div className="font-bold text-lg text-gray-500">{sym}</div>
                                                        <div className="text-[10px] text-blue-400 animate-pulse mt-2">Analizando...</div>
                                                    </div>
                                                ))
                                            }
                                        </>
                                    )}
                                </div>
                            </section>

                            {/* Panel de Configuración al Fondo */}
                            <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700 shadow-2xl">
                                <h2 className="text-xl font-bold mb-8 flex items-center border-b border-slate-700 pb-4">
                                    <span className="mr-2">⚙️</span> Configuración del Sistema
                                </h2>
                                {editConfig && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                        <div className="space-y-6">
                                            <div title="Pérdida máxima tolerable antes de disparar el Stop Loss de seguridad.">
                                                <label className="block text-xs text-gray-400 mb-1 whitespace-nowrap uppercase font-bold tracking-wider">Pérdida Máxima Inicial</label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="0.1"
                                                        value={Math.round((1 - editConfig.strategy.initial_sl_pct) * 1000) / 10} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, initial_sl_pct: 1 - (parseFloat(e.target.value) / 100)}})}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-right pr-10"
                                                    />
                                                    <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
                                                </div>
                                            </div>
                                            <div title="Ganancia mínima necesaria para que el Trailing Stop empiece a perseguir el precio.">
                                                <label className="block text-xs text-gray-400 mb-1 whitespace-nowrap uppercase font-bold tracking-wider">Primer Escalón (Take Profit)</label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="0.1"
                                                        value={Math.round((editConfig.strategy.initial_tp_pct - 1) * 1000) / 10} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, initial_tp_pct: 1 + (parseFloat(e.target.value) / 100)}})}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-right pr-10"
                                                    />
                                                    <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <div className="border-2 border-blue-500/50 bg-blue-500/10 p-4 rounded-xl shadow-lg shadow-blue-500/10"
                                                 title="VARIABLE CLAVE: Distancia (en %) que el Stop Loss mantendrá respecto al precio máximo alcanzado.">
                                                <label className="block text-xs text-blue-300 font-bold mb-1 whitespace-nowrap flex items-center uppercase tracking-wider">
                                                    <span className="mr-1">🔥</span> Subida de Piso (Trailing Stop)
                                                </label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="0.1"
                                                        value={Math.round((1 - (editConfig.strategy.trailing_sl_pct || 0.99)) * 1000) / 10} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, trailing_sl_pct: 1 - (parseFloat(e.target.value) / 100)}})}
                                                        className="w-full bg-slate-950 border border-blue-400/30 rounded p-2 text-sm text-right pr-10 font-bold text-blue-400"
                                                    />
                                                    <span className="absolute right-3 top-2 text-blue-400 text-sm">%</span>
                                                </div>
                                            </div>
                                            <div title="Meta de ganancia para incrementar el contador de 'Pasos' (Milestones).">
                                                <label className="block text-xs text-gray-400 mb-1 whitespace-nowrap uppercase font-bold tracking-wider">Siguiente Escalón (Trailing TP)</label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="0.1"
                                                        value={Math.round(((editConfig.strategy.trailing_tp_pct || 1.011) - 1) * 1000) / 10} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, trailing_tp_pct: 1 + (parseFloat(e.target.value) / 100)}})}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-right pr-10"
                                                    />
                                                    <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <div title="Porcentaje del saldo disponible que el bot asignará a cada nueva operación.">
                                                <label className="block text-xs text-gray-400 mb-1 whitespace-nowrap uppercase font-bold tracking-wider">Riesgo por Operación</label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="1"
                                                        value={Math.round(editConfig.strategy.risk_balance_pct * 100)} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, risk_balance_pct: parseFloat(e.target.value) / 100}})}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-right pr-10"
                                                    />
                                                    <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
                                                </div>
                                            </div>
                                            <div title="Puntaje de IA (0-10) necesario para que el activo aparezca como oportunidad de compra.">
                                                <label className="block text-xs text-gray-400 mb-1 whitespace-nowrap uppercase font-bold tracking-wider">Puntaje Mínimo de Compra</label>
                                                <div className="relative">
                                                    <input 
                                                        type="number" step="0.1"
                                                        value={editConfig.strategy.min_buy_score} 
                                                        onChange={e => setEditConfig({...editConfig, strategy: {...editConfig.strategy, min_buy_score: parseFloat(e.target.value)}})}
                                                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-right"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                        <div className="col-span-full border-t border-slate-700 pt-6">
                                            <label className="block text-xs text-gray-400 mb-2 uppercase font-bold tracking-wider">Watchlist (Símbolos a analizar)</label>
                                            <div className="flex flex-wrap gap-2 mb-4">
                                                {editConfig.watchlist.map(sym => (
                                                    <span key={sym} className="bg-slate-700 px-3 py-1 rounded-full text-xs flex items-center gap-2 group">
                                                        {sym}
                                                        <button 
                                                            onClick={() => setEditConfig({...editConfig, watchlist: editConfig.watchlist.filter(s => s !== sym)})}
                                                            className="text-gray-500 hover:text-red-400"
                                                        >
                                                            ×
                                                        </button>
                                                    </span>
                                                ))}
                                                <div className="flex gap-2">
                                                    <input 
                                                        type="text" 
                                                        placeholder="Símbolo..." 
                                                        value={newSymbol}
                                                        onChange={e => setNewSymbol(e.target.value.toUpperCase())}
                                                        className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-xs w-24"
                                                    />
                                                    <button 
                                                        onClick={() => { if(newSymbol && !editConfig.watchlist.includes(newSymbol)) setEditConfig({...editConfig, watchlist: [...editConfig.watchlist, newSymbol]}); setNewSymbol(""); }}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-xs font-bold"
                                                    >
                                                        +
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <button 
                                    onClick={saveConfig}
                                    className="mt-8 w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-600/20 transition-all uppercase tracking-widest"
                                >
                                    💾 Guardar Configuración del Sistema
                                </button>
                            </div>
                        </div>

                    {/* PANEL DE HISTORIAL DE OPERACIONES */}
                    <div className="mt-8 bg-slate-800/40 border border-slate-700 rounded-xl p-6">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold flex items-center">
                                <span className="mr-2">📜</span> Historial de Operaciones
                            </h2>
                            <div className="text-right">
                                <span className="text-sm text-gray-400 mr-3">Ganancia Total Acumulada:</span>
                                <span className={`text-2xl font-bold ${
                                    (status.history || []).reduce((acc, h) => acc + (h.profit_amount || 0), 0) >= 0 
                                    ? 'text-green-400' : 'text-red-400'
                                }`}>
                                    ${Math.round((status.history || []).reduce((acc, h) => acc + (h.profit_amount || 0), 0)).toLocaleString()}
                                </span>
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="text-xs text-gray-400 uppercase bg-slate-900/50">
                                    <tr>
                                        <th className="px-4 py-3 rounded-tl-lg">Fecha</th>
                                        <th className="px-4 py-3">Activo</th>
                                        <th className="px-4 py-3">Tipo de Salida</th>
                                        <th className="px-4 py-3 text-right">P. Compra</th>
                                        <th className="px-4 py-3 text-right">P. Venta</th>
                                        <th className="px-4 py-3 text-right">Cantidad</th>
                                        <th className="px-4 py-3 text-right">Rendimiento (%)</th>
                                        <th className="px-4 py-3 text-right rounded-tr-lg">Ganancia ($)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {!status.history || status.history.length === 0 ? (
                                        <tr>
                                            <td colSpan="8" className="px-4 py-8 text-center text-gray-500 italic">
                                                Aún no hay operaciones cerradas.
                                            </td>
                                        </tr>
                                    ) : (
                                        [...status.history].reverse().map((h, i) => {
                                            const isWin = h.profit_pct >= 0;
                                            return (
                                                <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                                                    <td className="px-4 py-3 text-gray-400">{h.date}</td>
                                                    <td className="px-4 py-3 font-bold">{h.symbol}</td>
                                                    <td className="px-4 py-3">
                                                        <span className="text-xs px-2 py-1 rounded bg-slate-700 text-gray-300">
                                                            {h.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right font-mono">${h.entry_price.toFixed(2)}</td>
                                                    <td className="px-4 py-3 text-right font-mono">${h.exit_price.toFixed(2)}</td>
                                                    <td className="px-4 py-3 text-right">{h.qty}</td>
                                                    <td className={`px-4 py-3 text-right font-bold ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                                                        {isWin ? '+' : ''}{h.profit_pct.toFixed(2)}%
                                                    </td>
                                                    <td className={`px-4 py-3 text-right font-bold ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                                                        ${h.profit_amount.toFixed(2)}
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    