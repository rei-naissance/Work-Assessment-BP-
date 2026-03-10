import { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from '../components/Toast';
import { Skeleton, SkeletonTable } from '../components/Skeleton';
import { EmptyOrders, EmptyUsers } from '../components/EmptyState';
import {
  pageContainer, pageTitle, card, cardPadded, cardHeader, cardBody,
  btnPrimary, btnSecondary, btnDanger, badge, badgeColors,
  tableWrapper, table, tableHead, th, td, tableRow, tableDivider,
  modalOverlay, modalContent, sectionTitle, sectionSubtitle, statusDot,
} from '../styles/shared';

interface User {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string | null;
}

interface Order {
  id: string;
  user_id: string;
  customer_email: string;
  customer_name: string;
  tier: string;
  amount_cents: number;
  payment_status: string;
  fulfillment_status: string;
  tracking_number: string;
  notes: string;
  shipped_at: string | null;
  binder_id: string | null;
  binder_status: string | null;
  has_pdf: boolean;
  unread_messages: number;
  created_at: string | null;
}

interface Readiness {
  overall_score: number;
  can_generate: boolean;
  blocking_issues: string[];
  sections: Record<string, {
    name: string;
    score: number;
    status: string;
    critical_missing: string[];
    warnings: string[];
    tips: string[];
  }>;
  feature_warnings: Array<{ feature: string; missing: string[]; step_to_fix: string }>;
  unknown_count: number | null;
}

interface OrderMessage {
  id: string;
  order_id: string;
  sender: 'admin' | 'user';
  message: string;
  read: boolean;
  created_at: string | null;
}

interface Feedback {
  id: string;
  type: string;
  message: string;
  page: string | null;
  user_email: string | null;
  status: string;
  created_at: string | null;
}

interface Pricing {
  standard_cents: number;
  premium_cents: number;
}

type Tab = 'orders' | 'users' | 'feedback' | 'pricing' | 'logic';

const STATUS_COLORS: Record<string, string> = {
  pending: badgeColors.yellow,
  processing: badgeColors.blue,
  shipped: badgeColors.purple,
  delivered: badgeColors.green,
  refunded: badgeColors.red,
  on_hold: badgeColors.orange,
};

export default function Admin() {
  const [tab, setTab] = useState<Tab>('orders');
  const [users, setUsers] = useState<User[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [rulesTree, setRulesTree] = useState<Record<string, any> | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pricingSaving, setPricingSaving] = useState(false);
  const { showToast } = useToast();

  // Form state for order editing
  const [editStatus, setEditStatus] = useState('');
  const [editTracking, setEditTracking] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [saving, setSaving] = useState(false);

  // Readiness, messages, hold
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [messages, setMessages] = useState<OrderMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [holdMessage, setHoldMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ordersRes, usersRes, feedbackRes, pricingRes, rulesRes] = await Promise.all([
        api.get('/admin/orders'),
        api.get('/admin/users'),
        api.get('/admin/feedback'),
        api.get('/admin/pricing'),
        api.get('/admin/rules-tree'),
      ]);
      setOrders(ordersRes.data);
      setUsers(usersRes.data);
      setFeedback(feedbackRes.data);
      setPricing({
        standard_cents: pricingRes.data.prices.standard,
        premium_cents: pricingRes.data.prices.premium,
      });
      setRulesTree(rulesRes.data.tree);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Access denied');
    } finally {
      setLoading(false);
    }
  };

  const openOrderDetail = async (order: Order) => {
    setSelectedOrder(order);
    setEditStatus(order.fulfillment_status);
    setEditTracking(order.tracking_number);
    setEditNotes(order.notes);
    setNewMessage('');
    setHoldMessage('');

    // Load readiness and messages in parallel
    setReadinessLoading(true);
    setMessagesLoading(true);
    try {
      const [readinessRes, messagesRes] = await Promise.all([
        api.get(`/admin/orders/${order.id}/readiness`),
        api.get(`/admin/orders/${order.id}/messages`),
      ]);
      setReadiness(readinessRes.data);
      setMessages(messagesRes.data);
    } catch {
      // Non-critical — modal still works without these
    } finally {
      setReadinessLoading(false);
      setMessagesLoading(false);
    }
  };

  const closeOrderDetail = () => {
    setSelectedOrder(null);
    setReadiness(null);
    setMessages([]);
  };

  const saveOrder = async () => {
    if (!selectedOrder) return;

    // Validate hold message requirement
    if (editStatus === 'on_hold' && selectedOrder.fulfillment_status !== 'on_hold' && !holdMessage.trim()) {
      showToast('Please enter a message explaining why the order is on hold', 'error');
      return;
    }

    setSaving(true);
    try {
      const wasShipped = editStatus === 'shipped' && selectedOrder.fulfillment_status !== 'shipped';
      const wasHeld = editStatus === 'on_hold' && selectedOrder.fulfillment_status !== 'on_hold';
      await api.patch(`/admin/orders/${selectedOrder.id}`, {
        fulfillment_status: editStatus,
        tracking_number: editTracking,
        notes: editNotes,
        hold_message: wasHeld ? holdMessage : '',
      });
      await loadData();
      closeOrderDetail();

      if (wasShipped) {
        showToast('Order marked as shipped. Customer notified.', 'success');
      } else if (wasHeld) {
        showToast('Order put on hold. Customer notified.', 'success');
      } else {
        showToast('Order updated successfully', 'success');
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail?.message || e.response?.data?.detail || 'Failed to update order', 'error');
    } finally {
      setSaving(false);
    }
  };

  const sendMessage = async () => {
    if (!selectedOrder || !newMessage.trim()) return;
    setSendingMessage(true);
    try {
      await api.post(`/admin/orders/${selectedOrder.id}/messages`, { message: newMessage.trim() });
      setNewMessage('');
      // Reload messages
      const res = await api.get(`/admin/orders/${selectedOrder.id}/messages`);
      setMessages(res.data);
      showToast('Message sent. Customer notified via email.', 'success');
    } catch {
      showToast('Failed to send message', 'error');
    } finally {
      setSendingMessage(false);
    }
  };

  const downloadPdf = async (orderId: string) => {
    try {
      showToast('Downloading PDF...', 'info');
      const response = await api.get(`/admin/orders/${orderId}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `binder_${orderId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showToast('PDF downloaded', 'success');
    } catch {
      showToast('Failed to download PDF', 'error');
    }
  };

  if (error) {
    return (
      <div className={pageContainer}>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <svg className="w-12 h-12 text-red-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-red-800 font-medium mb-1">Access Denied</p>
          <p className="text-red-600 text-sm mb-4">{error}</p>
        </div>
      </div>
    );
  }

  const pendingOrders = orders.filter(
    (o) => o.fulfillment_status === 'pending' && o.payment_status !== 'refunded'
  );

  const savePricing = async () => {
    if (!pricing) return;
    setPricingSaving(true);
    try {
      const res = await api.put('/admin/pricing', pricing);
      setPricing({
        standard_cents: res.data.prices.standard,
        premium_cents: res.data.prices.premium,
      });
      showToast('Pricing updated', 'success');
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to update pricing', 'error');
    } finally {
      setPricingSaving(false);
    }
  };

  return (
    <div className={pageContainer}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-6 mb-6">
        <h1 className={pageTitle}>Admin Dashboard</h1>
        {loading ? (
          <div className="flex flex-wrap gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-3 w-36">
                <Skeleton className="h-3 w-2/3 mb-2" />
                <Skeleton className="h-6 w-1/2" />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 min-w-[130px]">
              <p className="text-xs text-gray-500">Pending Orders</p>
              <p className="text-lg font-semibold text-yellow-600">{pendingOrders.length}</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 min-w-[130px]">
              <p className="text-xs text-gray-500">Total Orders</p>
              <p className="text-lg font-semibold text-gray-900">{orders.length}</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 min-w-[130px]">
              <p className="text-xs text-gray-500">Total Users</p>
              <p className="text-lg font-semibold text-gray-900">{users.length}</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 min-w-[130px]">
              <p className="text-xs text-gray-500">Revenue</p>
              <p className="text-lg font-semibold text-green-600">
                ${(orders.reduce((sum, o) => sum + (o.payment_status !== 'refunded' ? o.amount_cents : 0), 0) / 100).toFixed(0)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-8">
          <button
            onClick={() => setTab('orders')}
            className={`pb-3 text-sm font-medium border-b-2 transition ${
              tab === 'orders'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Orders
            {!loading && pendingOrders.length > 0 && (
              <span className={`ml-2 ${badge} ${badgeColors.yellow}`}>
                {pendingOrders.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab('users')}
            className={`pb-3 text-sm font-medium border-b-2 transition ${
              tab === 'users'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Users
            {!loading && (
              <span className={`ml-2 ${badge} ${badgeColors.gray}`}>
                {users.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab('feedback')}
            className={`pb-3 text-sm font-medium border-b-2 transition ${
              tab === 'feedback'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Feedback
            {!loading && feedback.filter(f => f.status === 'new').length > 0 && (
              <span className={`ml-2 ${badge} ${badgeColors.amber}`}>
                {feedback.filter(f => f.status === 'new').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab('pricing')}
            className={`pb-3 text-sm font-medium border-b-2 transition ${
              tab === 'pricing'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Pricing
          </button>
          <button
            onClick={() => setTab('logic')}
            className={`pb-3 text-sm font-medium border-b-2 transition ${
              tab === 'logic'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Logic
          </button>
        </nav>
      </div>

      {loading ? (
        <SkeletonTable rows={5} cols={tab === 'orders' ? 6 : 3} />
      ) : (
        <>
          {/* Orders Tab */}
          {tab === 'orders' && (
            orders.length === 0 ? (
              <div className={card}>
                <EmptyOrders />
              </div>
            ) : (
              <div className={card}>
                <div className={tableWrapper}>
                  <table className={table}>
                    <thead className={tableHead}>
                      <tr>
                        <th className={th}>Customer</th>
                        <th className={th}>Plan</th>
                        <th className={th}>Amount</th>
                        <th className={th}>Status</th>
                        <th className={th}>PDF</th>
                        <th className={th}>Date</th>
                        <th className={th}></th>
                      </tr>
                    </thead>
                    <tbody className={tableDivider}>
                      {orders.map((order) => (
                        <tr key={order.id} className={tableRow}>
                          <td className={td}>
                            <div className="font-medium text-gray-900">
                              {order.customer_name || 'No name'}
                            </div>
                            <div className="text-gray-500 text-xs">{order.customer_email}</div>
                          </td>
                          <td className={`${td} capitalize`}>{order.tier}</td>
                          <td className={td}>${(order.amount_cents / 100).toFixed(2)}</td>
                          <td className={td}>
                            <span
                              className={`${badge} ${
                                order.payment_status === 'refunded'
                                  ? STATUS_COLORS.refunded
                                  : STATUS_COLORS[order.fulfillment_status] || 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {order.payment_status === 'refunded'
                                ? 'Refunded'
                                : order.fulfillment_status === 'on_hold'
                                ? 'On Hold'
                                : order.fulfillment_status}
                            </span>
                            {order.unread_messages > 0 && (
                              <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-500 text-white text-[10px] font-bold">
                                {order.unread_messages}
                              </span>
                            )}
                          </td>
                          <td className={td}>
                            {order.has_pdf ? (
                              <button
                                onClick={() => downloadPdf(order.id)}
                                className="text-brand-600 hover:text-brand-700 text-xs font-medium"
                              >
                                Download
                              </button>
                            ) : (
                              <span className="text-gray-400 text-xs">Not ready</span>
                            )}
                          </td>
                          <td className={`${td} text-gray-500`}>
                            {order.created_at
                              ? new Date(order.created_at).toLocaleDateString()
                              : '-'}
                          </td>
                          <td className={td}>
                            <button
                              onClick={() => openOrderDetail(order)}
                              className="text-brand-600 hover:text-brand-700 font-medium text-sm"
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          )}

          {/* Users Tab */}
          {tab === 'users' && (
            users.length === 0 ? (
              <div className={card}>
                <EmptyUsers />
              </div>
            ) : (
              <div className={card}>
                <div className={tableWrapper}>
                  <table className={table}>
                    <thead className={tableHead}>
                      <tr>
                        <th className={th}>Email</th>
                        <th className={th}>Admin</th>
                        <th className={th}>Created</th>
                      </tr>
                    </thead>
                    <tbody className={tableDivider}>
                      {users.map((u) => (
                        <tr key={u.id} className={tableRow}>
                          <td className={td}>{u.email}</td>
                          <td className={td}>
                            {u.is_admin ? (
                              <span className="text-green-600 font-medium">Yes</span>
                            ) : (
                              <span className="text-gray-400">No</span>
                            )}
                          </td>
                          <td className={`${td} text-gray-500`}>
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          )}

          {/* Feedback Tab */}
          {tab === 'feedback' && (
            feedback.length === 0 ? (
              <div className={`${card} py-12 text-center`}>
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <p className="text-gray-500">No feedback yet</p>
                <p className="text-sm text-gray-400 mt-1">User reports will appear here</p>
              </div>
            ) : (
              <div className="space-y-3">
                {feedback.map((f) => (
                  <div key={f.id} className={`${card} p-4 border-l-4 ${
                    f.status === 'new' ? 'border-amber-500' :
                    f.status === 'reviewed' ? 'border-blue-500' :
                    'border-green-500'
                  }`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`${badge} ${
                          f.type === 'bug' ? badgeColors.red :
                          f.type === 'feedback' ? badgeColors.purple :
                          badgeColors.blue
                        }`}>
                          {f.type === 'bug' ? '🐛 Bug' : f.type === 'feedback' ? '💡 Idea' : '❓ Question'}
                        </span>
                        <span className={`${badge} ${
                          f.status === 'new' ? badgeColors.amber :
                          f.status === 'reviewed' ? badgeColors.blue :
                          badgeColors.green
                        }`}>
                          {f.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {f.status !== 'resolved' && (
                          <button
                            onClick={async () => {
                              try {
                                await api.patch(`/admin/feedback/${f.id}`, { status: f.status === 'new' ? 'reviewed' : 'resolved' });
                                await loadData();
                                showToast('Feedback updated', 'success');
                              } catch {
                                showToast('Failed to update', 'error');
                              }
                            }}
                            className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                          >
                            Mark as {f.status === 'new' ? 'Reviewed' : 'Resolved'}
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{f.message}</p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                      {f.user_email && <span>{f.user_email}</span>}
                      {f.page && <span>Page: {f.page}</span>}
                      {f.created_at && <span>{new Date(f.created_at).toLocaleString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}

          {tab === 'pricing' && (
            <div className={`${cardPadded} max-w-2xl`}>
              <h2 className={sectionTitle}>Pricing</h2>
              <p className={`${sectionSubtitle} mb-6`}>Update plan pricing for new checkouts. Existing paid orders are unaffected.</p>
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="text-sm font-medium text-gray-700">
                  Standard price (USD)
                  <input
                    type="number"
                    min={1}
                    className="mt-2 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={pricing ? pricing.standard_cents / 100 : ''}
                    onChange={(e) => setPricing((prev) => prev ? ({ ...prev, standard_cents: Math.round(Number(e.target.value) * 100) }) : prev)}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Premium price (USD)
                  <input
                    type="number"
                    min={1}
                    className="mt-2 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={pricing ? pricing.premium_cents / 100 : ''}
                    onChange={(e) => setPricing((prev) => prev ? ({ ...prev, premium_cents: Math.round(Number(e.target.value) * 100) }) : prev)}
                  />
                </label>
              </div>
              <div className="mt-6 flex items-center gap-3">
                <button
                  type="button"
                  onClick={savePricing}
                  disabled={!pricing || pricingSaving}
                  className={btnPrimary}
                >
                  {pricingSaving ? 'Saving...' : 'Save pricing'}
                </button>
                <span className="text-xs text-gray-400">Applies to new checkout sessions.</span>
              </div>
            </div>
          )}

          {tab === 'logic' && (
            <div className={cardPadded}>
              <h2 className={sectionTitle}>AI Rules Tree</h2>
              <p className={`${sectionSubtitle} mb-4`}>This is the root logic used to assemble binder content from a profile.</p>
              {rulesTree ? (
                <pre className="text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-4 overflow-x-auto">
                  {JSON.stringify(rulesTree, null, 2)}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">No rules tree loaded.</p>
              )}
            </div>
          )}
        </>
      )}

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className={modalOverlay}>
          <div className={modalContent}>
            <div className={cardHeader}>
              <div className="flex justify-between items-start">
                <div>
                  <h2 className={sectionTitle}>Order Details</h2>
                  <p className={sectionSubtitle}>{selectedOrder.customer_email}</p>
                </div>
                <button
                  onClick={closeOrderDetail}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className={`${cardBody} space-y-4`}>
              {/* Order Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Customer</p>
                  <p className="font-medium">{selectedOrder.customer_name || 'No name'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Plan</p>
                  <p className="font-medium capitalize">{selectedOrder.tier}</p>
                </div>
                <div>
                  <p className="text-gray-500">Amount</p>
                  <p className="font-medium">${(selectedOrder.amount_cents / 100).toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Order Date</p>
                  <p className="font-medium">
                    {selectedOrder.created_at
                      ? new Date(selectedOrder.created_at).toLocaleDateString()
                      : '-'}
                  </p>
                </div>
              </div>

              <hr className="border-gray-100" />

              {/* Status Update */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fulfillment Status
                </label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="on_hold">On Hold</option>
                  <option value="shipped">Shipped</option>
                  <option value="delivered">Delivered</option>
                </select>
              </div>

              {/* Hold message (when switching to on_hold) */}
              {editStatus === 'on_hold' && selectedOrder.fulfillment_status !== 'on_hold' && (
                <div>
                  <label className="block text-sm font-medium text-orange-700 mb-1">
                    Hold Reason (sent to customer)
                  </label>
                  <textarea
                    value={holdMessage}
                    onChange={(e) => setHoldMessage(e.target.value)}
                    placeholder="Explain what info is needed before the binder can ship..."
                    rows={3}
                    className="w-full border border-orange-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-orange-50"
                  />
                  <p className="text-xs text-orange-600 mt-1">Customer will be emailed this message</p>
                </div>
              )}

              {/* Tracking Number */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tracking Number
                </label>
                <input
                  type="text"
                  value={editTracking}
                  onChange={(e) => setEditTracking(e.target.value)}
                  placeholder="Enter tracking number"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                {editStatus === 'shipped' && selectedOrder.fulfillment_status !== 'shipped' && (
                  <p className="text-xs text-brand-600 mt-1 font-medium">
                    Customer will be emailed when you save
                  </p>
                )}
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Internal Notes
                </label>
                <textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Notes (not visible to customer)"
                  rows={2}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              {/* PDF Download */}
              {selectedOrder.has_pdf && (
                <div>
                  <button
                    onClick={() => downloadPdf(selectedOrder.id)}
                    className="w-full py-2 border border-brand-600 text-brand-600 rounded-lg text-sm font-medium hover:bg-brand-50 transition"
                  >
                    Download PDF for Printing
                  </button>
                </div>
              )}

              <hr className="border-gray-100" />

              {/* Readiness Score */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Binder Readiness</p>
                {readinessLoading ? (
                  <div className="bg-gray-50 rounded-lg p-3 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ) : readiness ? (
                  <div className="space-y-2">
                    {/* Badge */}
                    <div className="flex items-center gap-3">
                      <span className={`${badge} gap-1.5 px-3 py-1 font-semibold ${
                        readiness.overall_score >= 80 && readiness.blocking_issues.length === 0
                          ? badgeColors.green
                          : readiness.overall_score >= 50
                          ? badgeColors.yellow
                          : badgeColors.red
                      }`}>
                        <span className={`${statusDot} ${
                          readiness.overall_score >= 80 && readiness.blocking_issues.length === 0
                            ? 'bg-green-500'
                            : readiness.overall_score >= 50
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`} />
                        {readiness.overall_score >= 80 && readiness.blocking_issues.length === 0
                          ? 'Ready to print'
                          : readiness.overall_score >= 50
                          ? 'Review recommended'
                          : 'Needs attention'}
                      </span>
                      <span className="text-sm font-semibold text-gray-600">{readiness.overall_score}%</span>
                      {readiness.unknown_count != null && readiness.unknown_count > 0 && (
                        <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
                          {readiness.unknown_count} fill-in blanks
                        </span>
                      )}
                    </div>

                    {/* Blocking issues */}
                    {readiness.blocking_issues.length > 0 && (
                      <div className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                        <p className="font-semibold mb-1">Blocking Issues:</p>
                        <ul className="list-disc ml-4 space-y-0.5">
                          {readiness.blocking_issues.map((issue, i) => <li key={i}>{issue}</li>)}
                        </ul>
                      </div>
                    )}

                    {/* Section breakdown */}
                    <div className="grid grid-cols-2 gap-1.5">
                      {Object.entries(readiness.sections).map(([key, sec]) => (
                        <div key={key} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1">
                          <span className="text-gray-600 truncate">{sec.name}</span>
                          <span className={`font-semibold ml-1 ${
                            sec.status === 'complete' ? 'text-green-600' :
                            sec.status === 'needs_attention' ? 'text-amber-600' :
                            'text-red-600'
                          }`}>{sec.score}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Could not load readiness data</p>
                )}
              </div>

              <hr className="border-gray-100" />

              {/* Messages */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Messages</p>
                {messagesLoading ? (
                  <div className="bg-gray-50 rounded-lg p-3 animate-pulse">
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ) : (
                  <>
                    {messages.length > 0 ? (
                      <div className="space-y-2 mb-3 max-h-48 overflow-y-auto">
                        {messages.map((msg) => (
                          <div key={msg.id} className={`rounded-lg p-2.5 text-sm ${
                            msg.sender === 'admin'
                              ? 'bg-brand-50 border border-brand-100 ml-4'
                              : 'bg-gray-50 border border-gray-200 mr-4'
                          }`}>
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] font-semibold uppercase ${
                                msg.sender === 'admin' ? 'text-brand-600' : 'text-gray-500'
                              }`}>
                                {msg.sender === 'admin' ? 'You' : 'Customer'}
                              </span>
                              {msg.created_at && (
                                <span className="text-[10px] text-gray-400">
                                  {new Date(msg.created_at).toLocaleString()}
                                </span>
                              )}
                              {!msg.read && msg.sender === 'user' && (
                                <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">New</span>
                              )}
                            </div>
                            <p className="text-gray-700 whitespace-pre-wrap">{msg.message}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-gray-400 mb-3">No messages yet</p>
                    )}

                    {/* Send message */}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder="Send a message to the customer..."
                        className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                      />
                      <button
                        onClick={sendMessage}
                        disabled={!newMessage.trim() || sendingMessage}
                        className={`${btnPrimary} px-3 py-1.5`}
                      >
                        {sendingMessage ? '...' : 'Send'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
              <button
                onClick={closeOrderDetail}
                className={`flex-1 py-2 ${btnSecondary}`}
              >
                Cancel
              </button>
              <button
                onClick={saveOrder}
                disabled={saving}
                className={`flex-1 py-2 ${btnPrimary}`}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
