import { useTranslation } from "react-i18next";

export function Login({ onSubmit }: { onSubmit: (email: string, pw: string) => void }) {
  const { t } = useTranslation();
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(emailRef.current!.value, pwRef.current!.value); }}
          aria-labelledby="login-title">
      <h1 id="login-title">{t("login.title")}</h1>
      <label htmlFor="email">{t("login.email")}</label>
      <input id="email" type="email" required ref={emailRef} autoComplete="email" />
      <label htmlFor="pw">{t("login.password")}</label>
      <input id="pw" type="password" required ref={pwRef} autoComplete="current-password" />
      <button>{t("login.submit")}</button>
    </form>
  );
}
declare const emailRef: React.RefObject<HTMLInputElement>;
declare const pwRef: React.RefObject<HTMLInputElement>;
