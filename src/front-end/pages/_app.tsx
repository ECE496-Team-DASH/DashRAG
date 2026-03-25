import "@/styles/globals.css";
import "katex/dist/katex.min.css";
import type { AppProps } from "next/app";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/utils/AuthContext";

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter',
});

export default function App({ Component, pageProps }: AppProps<{}>) {
  return (
    <AuthProvider>
      <main className={`${inter.variable} font-sans`}>
        <Component {...pageProps} />
      </main>
    </AuthProvider>
  );
}
