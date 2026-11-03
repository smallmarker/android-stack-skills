package com.example.standard.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.standard.data.HomeRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

sealed interface HomeState {
    data object Loading : HomeState
    data class Ready(val message: String) : HomeState
    data object Error : HomeState
}
@HiltViewModel
class HomeViewModel @Inject constructor(private val repository: HomeRepository) : ViewModel() {
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
