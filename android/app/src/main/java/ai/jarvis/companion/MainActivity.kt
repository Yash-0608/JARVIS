package ai.jarvis.companion

import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Mic
import androidx.compose.material.icons.outlined.Phone
import androidx.compose.material.icons.outlined.Send
import androidx.compose.material.icons.outlined.Smartphone
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

private val Ink = Color(0xFF222632)
private val Muted = Color(0xFF858C99)
private val Blue = Color(0xFF416CF6)
private val Line = Color(0xFFE8EAF0)
private val Page = Color(0xFFF7F8FA)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = lightColorScheme(primary = Blue, background = Page, surface = Color.White)) { CompanionScreen() } }
    }
}

private suspend fun apiCall(base: String, path: String, method: String = "GET", body: JSONObject? = null, token: String? = null, pairSecret: String? = null): JSONObject = withContext(Dispatchers.IO) {
    val connection = (URL(base.trimEnd('/') + path).openConnection() as HttpURLConnection)
    try {
        connection.requestMethod = method
        connection.connectTimeout = 7000
        connection.readTimeout = 15000
        connection.setRequestProperty("Accept", "application/json")
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        }
        if (!token.isNullOrBlank()) connection.setRequestProperty("X-JARVIS-Device", token)
        if (!pairSecret.isNullOrBlank()) connection.setRequestProperty("X-JARVIS-Pair-Secret", pairSecret)
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val raw = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (code !in 200..299) throw IllegalStateException(JSONObject(raw.ifBlank { "{}" }).optString("detail", "Request failed ($code)"))
        JSONObject(raw.ifBlank { "{}" })
    } finally { connection.disconnect() }
}

@Composable
private fun CompanionScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var apiBase by remember { mutableStateOf("http://192.168.1.10:8000") }
    var pairingCode by remember { mutableStateOf("") }
    var deviceName by remember { mutableStateOf(android.os.Build.MODEL.ifBlank { "My Android phone" }) }
    var requestId by remember { mutableStateOf("") }
    var clientSecret by remember { mutableStateOf("") }
    var deviceToken by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Not connected") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var input by remember { mutableStateOf("") }
    var conversation by remember { mutableStateOf(listOf<Pair<String, String>>("JARVIS" to "Pair with your Windows desktop to begin.")) }
    var phoneNumber by remember { mutableStateOf("") }
    val tts = remember { TextToSpeech(context) {} }
    DisposableEffect(tts) { onDispose { tts.shutdown() } }

    val voiceLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            val spoken = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull().orEmpty()
            if (spoken.isNotBlank()) { input = spoken; }
        }
    }

    LaunchedEffect(requestId, clientSecret, apiBase, deviceToken) {
        if (requestId.isBlank() || clientSecret.isBlank() || deviceToken.isNotBlank()) return@LaunchedEffect
        while (deviceToken.isBlank()) {
            try {
                val path = "/api/pairing/status/$requestId"
                val result = apiCall(apiBase, path, pairSecret = clientSecret)
                val next = result.optString("state", "pending")
                status = when (next) { "accepted" -> "Connected"; "rejected" -> "Request declined"; else -> "Waiting for Windows approval" }
                if (next == "accepted") {
                    deviceToken = result.optString("device_token")
                    if (deviceToken.isNotBlank()) { error = ""; break }
                }
                if (next == "rejected") break
            } catch (_: Exception) { status = "Waiting for desktop…" }
            delay(2500)
        }
    }

    fun connect() {
        if (apiBase.isBlank() || pairingCode.trim().length < 6) { error = "Enter the Windows API address and six-character pairing code."; return }
        scope.launch {
            busy = true; error = ""
            try {
                val result = apiCall(apiBase, "/api/pairing/request", "POST", JSONObject().put("code", pairingCode.trim()).put("device_name", deviceName).put("device_platform", "Android"))
                requestId = result.optString("request_id")
                clientSecret = result.optString("client_secret")
                status = "Waiting for Windows approval"
                if (requestId.isBlank() || clientSecret.isBlank()) error = "The server returned an incomplete pairing response."
            } catch (e: Exception) { error = e.message ?: "Could not request pairing. Check the LAN address and code." }
            finally { busy = false }
        }
    }

    fun sendChat(text: String) {
        if (text.isBlank() || deviceToken.isBlank()) return
        scope.launch {
            busy = true; error = ""; conversation = conversation + ("You" to text)
            try {
                val result = apiCall(apiBase, "/api/phone/chat", "POST", JSONObject().put("message", text), deviceToken)
                val answer = result.optString("response", "I received an empty response.")
                conversation = conversation + ("JARVIS" to answer)
                tts.language = Locale("en", "IN")
                tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "jarvis-response")
                input = ""
            } catch (e: Exception) { error = e.message ?: "Chat request failed" }
            finally { busy = false }
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = Page) {
        Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(11.dp)) {
                Surface(shape = RoundedCornerShape(13.dp), color = Ink, modifier = Modifier.size(43.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Smartphone, null, tint = Color.White) } }
                Column(Modifier.weight(1f)) { Text("JARVIS", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = Ink, letterSpacing = 1.5.sp); Text("PHONE COMPANION", fontSize = 9.sp, color = Muted, letterSpacing = 1.5.sp) }
                Surface(shape = RoundedCornerShape(30.dp), color = if (deviceToken.isNotBlank()) Color(0xFFE9F8F0) else Color(0xFFEFF1F5)) { Text(status, modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp), fontSize = 10.sp, color = if (deviceToken.isNotBlank()) Color(0xFF268A62) else Muted) }
            }
            Spacer(Modifier.height(22.dp))
            if (deviceToken.isBlank()) {
                Text("Connect to your PC", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = Ink)
                Spacer(Modifier.height(6.dp)); Text("Use the same request-and-accept flow as PhoneCast. Your Windows app must be running on the same trusted Wi-Fi network.", fontSize = 12.sp, color = Muted, lineHeight = 18.sp)
                Spacer(Modifier.height(18.dp))
                Card(colors = CardDefaults.cardColors(containerColor = Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, Line), shape = RoundedCornerShape(15.dp)) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("CONNECTION DETAILS", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp, color = Muted)
                        OutlinedTextField(value = apiBase, onValueChange = { apiBase = it }, label = { Text("Windows API address") }, placeholder = { Text("http://192.168.1.x:8000") }, singleLine = true, modifier = Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
                        OutlinedTextField(value = deviceName, onValueChange = { deviceName = it }, label = { Text("Device name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(value = pairingCode, onValueChange = { pairingCode = it.uppercase().take(6) }, label = { Text("6-character pairing code") }, singleLine = true, modifier = Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii))
                        Button(onClick = { connect() }, enabled = !busy, modifier = Modifier.fillMaxWidth().height(47.dp), shape = RoundedCornerShape(10.dp)) { Text(if (busy) "Connecting…" else "Request connection") }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top) { Icon(Icons.Outlined.Wifi, null, tint = Blue, modifier = Modifier.size(16.dp)); Text("For development, the PC firewall must allow port 8000 on a trusted private network. Do not expose this HTTP service to the internet.", fontSize = 10.sp, color = Muted, lineHeight = 15.sp) }
                    }
                }
                if (requestId.isNotBlank()) { Spacer(Modifier.height(15.dp)); Text(status, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, color = Blue) }
            } else {
                Text("You're connected.", fontSize = 23.sp, fontWeight = FontWeight.Bold, color = Ink)
                Text("Talk to your local JARVIS model from your phone.", fontSize = 12.sp, color = Muted, modifier = Modifier.padding(top = 5.dp, bottom = 14.dp))
                Card(Modifier.weight(1f).fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, Line), shape = RoundedCornerShape(14.dp)) {
                    LazyColumn(modifier = Modifier.fillMaxSize().padding(13.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
                        items(conversation) { (speaker, text) ->
                            Column {
                                Text(speaker.uppercase(), fontSize = 9.sp, fontWeight = FontWeight.Bold, color = if (speaker == "JARVIS") Blue else Muted, letterSpacing = 1.sp)
                                Text(text, fontSize = 13.sp, color = Ink, lineHeight = 19.sp, modifier = Modifier.padding(top = 4.dp))
                            }
                        }
                    }
                }
                Spacer(Modifier.height(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    OutlinedTextField(value = input, onValueChange = { input = it }, modifier = Modifier.weight(1f), placeholder = { Text("Talk to JARVIS…") }, shape = RoundedCornerShape(12.dp), maxLines = 3)
                    IconButton(onClick = {
                        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-IN")
                            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to JARVIS")
                        }
                        try { voiceLauncher.launch(intent) } catch (_: Exception) { Toast.makeText(context, "Speech recognition is unavailable on this device.", Toast.LENGTH_SHORT).show() }
                    }) { Icon(Icons.Outlined.Mic, "Voice input", tint = Blue) }
                    IconButton(onClick = { sendChat(input) }, enabled = !busy && input.isNotBlank()) { Icon(Icons.Outlined.Send, "Send", tint = Blue) }
                }
                Spacer(Modifier.height(12.dp))
                Card(colors = CardDefaults.cardColors(containerColor = Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, Line), shape = RoundedCornerShape(12.dp)) {
                    Column(Modifier.padding(13.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Outlined.Phone, null, tint = Muted); Spacer(Modifier.width(8.dp)); Text("Calls", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Ink) }
                        Text("Direct call handling isn't enabled yet. Enter a number to open Android's dialer; no call is placed automatically.", fontSize = 10.sp, lineHeight = 15.sp, color = Muted, modifier = Modifier.padding(vertical = 6.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            OutlinedTextField(value = phoneNumber, onValueChange = { phoneNumber = it }, label = { Text("Phone number") }, modifier = Modifier.weight(1f), singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone))
                            Spacer(Modifier.width(8.dp))
                            OutlinedButton(onClick = { if (phoneNumber.isNotBlank()) { try { context.startActivity(Intent(Intent.ACTION_DIAL, android.net.Uri.parse("tel:${android.net.Uri.encode(phoneNumber)}"))) } catch (_: Exception) { error = "Could not open the phone dialer." } } }) { Text("Open dialer") }
                        }
                    }
                }
            }
            if (error.isNotBlank()) { Spacer(Modifier.height(9.dp)); Text(error, color = Color(0xFFB54141), fontSize = 11.sp) }
            Spacer(Modifier.height(9.dp)); Text("JARVIS COMPANION · PRIVATE BY DESIGN", fontSize = 8.sp, letterSpacing = 1.2.sp, color = Color(0xFFA3A8B1), modifier = Modifier.align(Alignment.CenterHorizontally))
        }
    }
}
