package com.example.lightweight

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.lightweight.ui.AppTheme
import com.example.lightweight.ui.HomeState
import com.example.lightweight.ui.HomeViewModel
class MainActivity : ComponentActivity() {
    private val model: HomeViewModel by viewModels()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val state by model.state.collectAsStateWithLifecycle()
            AppTheme {
                Scaffold { padding ->
                    Column(Modifier.fillMaxSize().padding(padding).padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Text("LightweightDemo", style = MaterialTheme.typography.headlineMedium)
                        when (val current = state) {
                            HomeState.Loading -> CircularProgressIndicator()
                            is HomeState.Ready -> Text(current.message)
                            HomeState.Error -> {
                                Text("Could not load this page.")
                                Button(onClick = model::refresh) { Text("Try again") }
                            }
                        }
                    }
                }
            }
        }
    }
}
