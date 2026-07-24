import {
  CheckCircle2,
  CreditCard,
  GraduationCap,
  ShoppingBag,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { EmptyState, ErrorNotice, Loading } from "./UI";

const number = new Intl.NumberFormat("fa-IR");

export default function Cart({ notify, onNavigate }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [error, setError] = useState("");
  const total = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.course.price || 0), 0),
    [items],
  );

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await api.cart());
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const remove = async (itemId) => {
    try {
      await api.removeFromCart(itemId);
      setItems((value) => value.filter((item) => item.id !== itemId));
      notify("دوره از سبد خرید حذف شد.");
    } catch (reason) {
      notify(reason.message, "error");
    }
  };

  const checkout = async () => {
    setPaying(true);
    try {
      const response = await api.checkout();
      setReceipt(response);
      setItems([]);
      notify("پرداخت شبیه‌سازی شد؛ دوره‌ها همین حالا فعال شدند.");
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setPaying(false);
    }
  };

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">خرید دوره</span>
          <h1>سبد خرید</h1>
          <p>درگاه این نسخه شبیه‌سازی شده و با زدن پرداخت، تراکنش مستقیم تأیید می‌شود.</p>
        </div>
        <span className="heading-icon">
          <ShoppingBag size={28} />
        </span>
      </div>

      {receipt && (
        <div className="payment-success card">
          <CheckCircle2 size={37} />
          <div>
            <span className="eyebrow">پرداخت موفق</span>
            <h2>دوره به حساب شما اضافه شد</h2>
            <p>
              شماره پیگیری: {receipt.purchases.map((item) => item.reference).join("، ")}
            </p>
          </div>
          <button
            type="button"
            className="button button--primary"
            onClick={() => onNavigate("courses")}
          >
            شروع یادگیری
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => onNavigate("transactions")}
          >
            مشاهده تراکنش
          </button>
        </div>
      )}

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="سبد خرید را آماده می‌کنیم…" />
      ) : items.length ? (
        <div className="checkout-layout">
          <div className="cart-items">
            {items.map((item) => (
              <article className="card cart-row" key={item.id}>
                <span className="cart-row__cover">
                  <GraduationCap size={30} />
                </span>
                <div>
                  <span className="eyebrow">{item.course.category_name}</span>
                  <h2>{item.course.title}</h2>
                  <small>
                    {number.format(item.course.lesson_count)} درس ·{" "}
                    {number.format(item.course.duration_minutes)} دقیقه
                  </small>
                </div>
                <strong>{number.format(item.course.price)} تومان</strong>
                <button
                  type="button"
                  className="icon-button danger-button"
                  onClick={() => remove(item.id)}
                  aria-label="حذف از سبد"
                >
                  <Trash2 size={18} />
                </button>
              </article>
            ))}
          </div>
          <aside className="card order-summary">
            <span className="eyebrow">خلاصه سفارش</span>
            <h2>{number.format(items.length)} دوره</h2>
            <div>
              <span>مبلغ کل</span>
              <strong>{number.format(total)} تومان</strong>
            </div>
            <div>
              <span>تخفیف</span>
              <strong>۰ تومان</strong>
            </div>
            <div className="order-summary__total">
              <span>قابل پرداخت</span>
              <strong>{number.format(total)} تومان</strong>
            </div>
            <button
              type="button"
              className="button button--primary button--wide"
              onClick={checkout}
              disabled={paying}
            >
              <CreditCard size={19} />
              {paying ? "در حال تأیید…" : "پرداخت و فعال‌سازی مستقیم"}
            </button>
            <small>این پرداخت آزمایشی است و به درگاه بانکی متصل نمی‌شود.</small>
          </aside>
        </div>
      ) : !receipt ? (
        <EmptyState
          icon={ShoppingBag}
          title="سبد خرید خالی است"
          description="از بخش کشف دوره‌ها یک دوره پولی انتخاب کن."
          action={
            <button
              type="button"
              className="button button--primary"
              onClick={() => onNavigate("courses")}
            >
              مشاهده دوره‌ها
            </button>
          }
        />
      ) : null}
    </section>
  );
}
