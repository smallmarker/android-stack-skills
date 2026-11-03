package com.example.standard.data

import javax.inject.Inject

interface HomeRepository {
    suspend fun greeting(): String
}
class DefaultHomeRepository @Inject constructor() : HomeRepository {
    override suspend fun greeting(): String = "Your app is ready."
}
