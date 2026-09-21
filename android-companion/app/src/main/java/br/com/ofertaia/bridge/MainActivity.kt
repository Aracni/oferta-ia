package br.com.ofertaia.bridge

import android.net.Uri
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var web: WebView
    private val portal = "https://www.mercadolivre.com.br/afiliados/linkbuilder"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.userAgentString += " OFERTA-IA-Bridge/1.0"
        web.webViewClient = WebViewClient()
        CookieManager.getInstance().setAcceptCookie(true)
        setContentView(web)

        val incoming = intent?.data
        if (incoming?.scheme == "ofertaia" && incoming.host == "affiliate") {
            val url = incoming.getQueryParameter("url")
            if (!url.isNullOrBlank()) {
                web.loadUrl(portal)
                web.postDelayed({ generate(url) }, 1800)
                return
            }
        }
        web.loadUrl(portal)
    }

    private fun generate(productUrl: String) {
        val safe = productUrl.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        val js = """
            (async function() {
              try {
                const r = await fetch('https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink', {
                  method:'POST',
                  credentials:'include',
                  headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},
                  body:JSON.stringify({urls:['$safe'],tag:''})
                });
                const d=await r.text();
                location.href='ofertaia://affiliate/result?data='+encodeURIComponent(d);
              } catch(e) {
                location.href='ofertaia://affiliate/result?error='+encodeURIComponent(String(e));
              }
            })();
        """.trimIndent()
        web.evaluateJavascript(js, null)
    }

    override fun onNewIntent(intent: android.content.Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
    }
}
