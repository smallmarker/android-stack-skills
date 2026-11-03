package com.example.lightweight.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.lightweight.data.HomeRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface HomeState {
    data object Loading : HomeState
    data class Ready(val message: String) : HomeState
    data object Error : HomeState
}
class HomeViewModel(private val repository: HomeRepository = HomeRepository()) : ViewModel() {
    private val mutableState = MutableStateFlow<HomeState>(HomeState.Loading)
    val state = mutableState.asStateFlow()
    init { refresh() }
    fun refresh() {
        viewModelScope.launch {
            mutableState.value = HomeState.Loading
            try {
                mutableState.value = HomeState.Ready(repository.greeting())
            } catch (error: CancellationException) { throw error
            } catch (error: Exception) { mutableState.value = HomeState.Error }
        }
    }
}
