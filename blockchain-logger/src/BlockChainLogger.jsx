import React, { useState, useEffect, useRef } from 'react';
import { Activity, Server, Wallet, Pickaxe, Terminal } from 'lucide-react';
import io from 'socket.io-client';

const BlockchainLogger = () => {
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isTestRunning, setIsTestRunning] = useState(false);
    const [selectedLogSection, setSelectedLogSection] = useState(null); 
    const socketRef = useRef(null);

    const testRef = useRef(null);
    const bootstrapRef = useRef(null);
    const minerRef = useRef(null);
    const walletRef = useRef(null);
    const errorRef = useRef(null);

    useEffect(() => {
        socketRef.current = io('https://comp41770project-kartikeya-sharma.onrender.com/');

        socketRef.current.on('connect', () => setIsConnected(true));
        socketRef.current.on('disconnect', () => setIsConnected(false));

        socketRef.current.on('log', (logEntry) => {
            setLogs(prev => [...prev, logEntry]);
        });

        socketRef.current.on('test_started', () => {
            setIsTestRunning(true);
            setLogs([]);
        });

        socketRef.current.on('test_completed', () => setIsTestRunning(false));
        socketRef.current.on('test_error', () => setIsTestRunning(false));
        socketRef.current.on('test_stopped', () => setIsTestRunning(false));

        return () => socketRef.current.disconnect();
    }, []);

    // Auto-scroll
    useEffect(() => {
        [testRef, bootstrapRef, minerRef, walletRef, errorRef].forEach(ref => {
            if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
        });
    }, [logs]);

    const startTest = () => socketRef.current.emit('start_test');
    const clearLogs = () => setLogs([]);

    // Filters
    const testLogs = logs.filter(log => /\[TEST\]/.test(log.message));
    const bootstrapLogs = logs.filter(log => /\[BOOTSTRAP NODE\]/.test(log.message));
    const minerLogs = logs.filter(log => /\[MINER \d+\]/.test(log.message));
    const walletLogs = logs.filter(log => /\[WALLET .+?\]/.test(log.message));
    const errorLogs = logs.filter(log => /\[ERROR\]/.test(log.message));

    // Modal to show entire log section
    const SectionModal = ({ title, logs, onClose }) => (
        <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={onClose}
        >
            <div
                className="bg-white rounded p-6 max-w-4xl max-h-[80vh] overflow-auto shadow-lg"
                onClick={e => e.stopPropagation()}
            >
                <h3 className="text-xl font-bold mb-4">{title} - Full Logs</h3>
                <div className="font-mono text-sm overflow-x-auto whitespace-nowrap max-w-full border rounded p-2 bg-gray-100 text-left">
                    {logs.length === 0 ? (
                        <div className="text-gray-500">No logs yet...</div>
                    ) : (
                        logs.map((log, idx) => (
                            <div key={idx} className="py-0.5">
                                <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                                <span className="text-gray-800">{log.message}</span>
                            </div>
                        ))
                    )}
                </div>
                <button
                    className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                    onClick={onClose}
                >
                    Close
                </button>
            </div>
        </div>
    );

    const LogSection = ({ title, logs, icon: Icon, scrollRef }) => {
        const [selectedLog, setSelectedLog] = useState(null);

        return (
            <>
                <div className="bg-white rounded border shadow-sm h-80 flex flex-col">
                    {/* Clickable header to open modal */}
                    <div
                        className="bg-gray-200 text-black px-3 py-2 flex items-center gap-2 cursor-pointer select-none"
                        onClick={() => setSelectedLogSection({ title, logs })}
                        title="Click to view full logs"
                    >
                        <Icon size={18} />
                        <h2 className="font-medium text-sm">{title}</h2>
                        <span className="ml-auto bg-gray-300 px-2 rounded text-xs">{logs.length}</span>
                    </div>

                    <div
                        ref={scrollRef}
                        className="flex-1 overflow-y-auto overflow-x-auto bg-gray-50 p-2 font-mono text-[11px] whitespace-nowrap text-left"
                    >
                        {logs.length === 0 ? (
                            <div className="text-gray-400 text-center py-4">No logs yet...</div>
                        ) : (
                            logs.map((log, idx) => (
                                <div
                                    key={idx}
                                    className="py-0.5 px-1 cursor-pointer hover:bg-gray-200 rounded max-w-full"
                                    onClick={() => setSelectedLog(log)}
                                    title="Click to view details"
                                >
                                    <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                                    <span className="text-gray-800">{log.message}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Individual log details modal */}
                {selectedLog && (
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                        onClick={() => setSelectedLog(null)}
                    >
                        <div
                            className="bg-white rounded p-6 max-w-lg max-h-[80vh] overflow-auto shadow-lg"
                            onClick={e => e.stopPropagation()}
                        >
                            <h3 className="text-xl font-bold mb-4">{title} - Log Details</h3>
                            <pre className="whitespace-pre-wrap text-sm font-mono">
                                {JSON.stringify(selectedLog, null, 2)}
                            </pre>
                            <button
                                className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                                onClick={() => setSelectedLog(null)}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                )}
            </>
        );
    };

    return (
        <div className="min-h-screen w-full px-6 py-6 bg-gray-100">
            {/* Header */}
            <div className="bg-white rounded shadow p-6 mb-6 w-full">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-gray-600">Real-time blockchain test logs</p>
                    </div>

                    <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                    <div
                                        className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'
                                            }`}
                                    ></div>
                                    <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
                                </div>

                                <button
                                    onClick={startTest}
                                    disabled={!isConnected || isTestRunning}
                                    className={`px-5 py-2 rounded text-white ${isTestRunning ? 'bg-gray-400' : 'bg-blue-500'
                                        }`}
                                >
                                    {isTestRunning ? 'Running...' : 'Start Test'}
                                </button>

                                {/* NEW STOP TEST BUTTON */}
                                <button
                                    onClick={() => socketRef.current.emit('stop_test')}
                                    disabled={!isTestRunning}
                                    className={`px-5 py-2 rounded text-white ${isTestRunning ? 'bg-red-500 hover:bg-red-600' : 'bg-gray-400 cursor-not-allowed'
                                        }`}
                                    title="Stop blockchain test"
                                >
                                    Stop Test
                                </button>

                                <button
                                    onClick={clearLogs}
                                    className="px-5 py-2 rounded bg-red-500 text-white"
                                >
                                    Clear
                                </button>
                        </div>
                    </div>
                </div>

                {/* Grid */}
                <div className="grid grid-cols-3 gap-4 w-full">
                    <LogSection title="Bootstrap Node" logs={bootstrapLogs} icon={Server} scrollRef={bootstrapRef} />
                    <LogSection title="Miners" logs={minerLogs} icon={Pickaxe} scrollRef={minerRef} />
                    <LogSection title="Wallets" logs={walletLogs} icon={Wallet} scrollRef={walletRef} />
                    <LogSection title="Test Logs" logs={testLogs} icon={Terminal} scrollRef={testRef} />
                    <LogSection title="Errors" logs={errorLogs} icon={Activity} scrollRef={errorRef} />
                </div>

                {/* Modal for full section logs */}
                {selectedLogSection && (
                    <SectionModal
                        title={selectedLogSection.title}
                        logs={selectedLogSection.logs}
                        onClose={() => setSelectedLogSection(null)}
                    />
                )}
            </div>
            );
};

            export default BlockchainLogger;
