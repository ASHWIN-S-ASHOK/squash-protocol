package com.squash.core.dict

import com.squash.core.model.SquashDictionary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update

/**
 * Thread-safe in-memory store for SQUASH dictionaries.
 *
 * Dictionaries are keyed by their schema name (e.g., `"user"`) and the store
 * maintains the latest version for each schema. Clients use this to:
 *
 * 1. Cache dictionaries received from servers (avoiding redundant `__dict` transfers).
 * 2. Look up the current dictionary for a schema when decoding responses.
 * 3. Determine whether their cached dict is stale compared to a server's dict ID.
 */
class DictionaryStore {

    private val store = MutableStateFlow<Map<String, SquashDictionary>>(emptyMap())

    /**
     * Stores or updates a dictionary. If a dictionary for the same schema
     * already exists, it is replaced only if the new version is higher.
     *
     * @param dictionary The dictionary to store.
     * @return `true` if the dictionary was stored (new or higher version), `false` if skipped.
     */
    fun put(dictionary: SquashDictionary): Boolean {
        var updated = false
        store.update { current ->
            val existing = current[dictionary.schemaName]
            if (existing != null && existing.version >= dictionary.version) {
                current
            } else {
                updated = true
                current + (dictionary.schemaName to dictionary)
            }
        }
        return updated
    }

    /**
     * Retrieves the cached dictionary for a schema name.
     *
     * @param schemaName The schema name (e.g., `"user"`).
     * @return The cached [SquashDictionary], or `null` if not found.
     */
    fun get(schemaName: String): SquashDictionary? = store.value[schemaName]

    /**
     * Retrieves a dictionary by its full dictId (e.g., `"user_v1"`).
     *
     * @param dictId The full dictionary identifier.
     * @return The cached [SquashDictionary] if it matches, or `null`.
     */
    fun getByDictId(dictId: String): SquashDictionary? {
        val schemaName = dictId.substringBeforeLast("_v")
        val dict = store.value[schemaName]
        return if (dict?.dictId == dictId) dict else null
    }

    /**
     * Checks whether the client's dict is current for a given server dictId.
     *
     * @param serverDictId The dictId reported by the server.
     * @return `true` if the client already has this exact dictionary version.
     */
    fun isCurrent(serverDictId: String): Boolean {
        return getByDictId(serverDictId) != null
    }

    /**
     * Returns the dictId for a schema, or `null` if no dict is cached.
     */
    fun getDictId(schemaName: String): String? = store.value[schemaName]?.dictId

    /**
     * Removes the dictionary for a schema.
     */
    fun remove(schemaName: String) {
        store.update { it - schemaName }
    }

    /** Clears all cached dictionaries. */
    fun clear() {
        store.update { emptyMap() }
    }

    /** Returns the number of cached dictionaries. */
    val size: Int get() = store.value.size
}
