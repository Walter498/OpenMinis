import Foundation

/// Reads and writes PendingShare data to the App Group shared container.
/// Compiled into both the main app target and the Share Extension target.
enum SharedContainerStore {
    static let appGroupID = "group.com.openminis.app"

    static let appGroupContainer = FileManager.default.containerURL(
        forSecurityApplicationGroupIdentifier: appGroupID
    )

    /// Keep the selected root stable for the lifetime of this process. A
    /// sideloaded build may not have an App Group entitlement after re-signing.
    /// Its main-app data still needs a persistent home inside its own sandbox.
    static let storageContainerRoot: URL = {
        let fm = FileManager.default
        let root = resolvedStorageRoot(
            groupContainer: appGroupContainer,
            libraryDirectory: fm.urls(for: .libraryDirectory, in: .userDomainMask)[0]
        )
        try? fm.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }()

    static func resolvedStorageRoot(groupContainer: URL?, libraryDirectory: URL) -> URL {
        groupContainer ?? libraryDirectory.appendingPathComponent("MinisStandaloneStorage", isDirectory: true)
    }

    private static let pendingShareKey = "pendingShare"

    static var sharedDefaults: UserDefaults? {
        UserDefaults(suiteName: appGroupID)
    }

    /// Directory in the shared container for transferring attachment files.
    static var sharedFileDirectory: URL? {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: appGroupID)?
            .appendingPathComponent("ShareExtension", isDirectory: true)
    }

    // MARK: - Write (called by Share Extension)

    static func savePendingShare(_ share: PendingShare) {
        guard let defaults = sharedDefaults else { return }
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        if let data = try? encoder.encode(share) {
            defaults.set(data, forKey: pendingShareKey)
            defaults.synchronize()
        }
    }

    // MARK: - Read & Consume (called by main app)

    static func loadPendingShare() -> PendingShare? {
        guard let defaults = sharedDefaults,
              let data = defaults.data(forKey: pendingShareKey) else { return nil }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try? decoder.decode(PendingShare.self, from: data)
    }

    static func clearPendingShare() {
        sharedDefaults?.removeObject(forKey: pendingShareKey)
        sharedDefaults?.synchronize()
    }

    /// Remove all files from the shared transfer directory.
    static func cleanSharedFiles() {
        guard let dir = sharedFileDirectory else { return }
        let fm = FileManager.default
        if let files = try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) {
            for file in files {
                try? fm.removeItem(at: file)
            }
        }
    }
}
