#!/usr/bin/env python3
"""Compile the shipping root resolver and test both storage modes on macOS."""
from pathlib import Path
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
store = (repo / 'src/ios/Shared/SharedContainerStore.swift').read_text()
start = store.index('static func resolvedStorageRoot(')
opening = store.index('{', start)
depth = 1
end = opening + 1
while depth:
    depth += (store[end] == '{') - (store[end] == '}')
    end += 1
resolver = store[start:end]

swift = '''import Foundation

enum StorageUnderTest {
RESOLVER
}

func check(_ value: @autoclosure () -> Bool, _ label: String) {
    guard value() else { fatalError(label) }
    print("PASS: " + label)
}
let fm = FileManager.default
let temporary = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
try fm.createDirectory(at: temporary, withIntermediateDirectories: true)
defer { try? fm.removeItem(at: temporary) }
let library = temporary.appendingPathComponent("Library")
let group = temporary.appendingPathComponent("Group")
let shared = StorageUnderTest.resolvedStorageRoot(groupContainer: group, libraryDirectory: library)
check(shared == group, "entitled builds keep the exact App Group root")
let local = StorageUnderTest.resolvedStorageRoot(groupContainer: nil, libraryDirectory: library)
check(local.path == library.appendingPathComponent("MinisStandaloneStorage").path,
      "missing App Group selects persistent Library storage")
let provider = local.appendingPathComponent("MinisFileProvider")
let config = local.appendingPathComponent("MinisConfig")
check(provider != config, "private configs stay outside user file roots")
for name in ["memory", "skills", "shared"] {
    let directory = provider.appendingPathComponent(name)
    try fm.createDirectory(at: directory, withIntermediateDirectories: true)
    let file = directory.appendingPathComponent("roundtrip.txt")
    try "persistent content".write(to: file, atomically: true, encoding: .utf8)
    let reopened = StorageUnderTest.resolvedStorageRoot(groupContainer: nil, libraryDirectory: library)
    let saved = try String(contentsOf: reopened.appendingPathComponent("MinisFileProvider/" + name + "/roundtrip.txt"), encoding: .utf8)
    check(saved == "persistent content", name + " survives storage root re-resolution")
}
check(StorageUnderTest.resolvedStorageRoot(groupContainer: group, libraryDirectory: library) == group,
      "an entitled installation continues using its shared root")
'''.replace('RESOLVER', resolver)

with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / 'StorageTests.swift'
    executable = Path(directory) / 'StorageTests'
    source.write_text(swift)
    subprocess.run(['swiftc', str(source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)

budget = (repo / 'src/ios/Agent/Chat/AIChatViewModel+RequestBudget.swift').read_text()
for accessor in ['minisAppGroupRoot', 'minisConfigRoot']:
    body = budget.split('static var ' + accessor + ': URL {', 1)[1].split('\n    }', 1)[0]
    assert 'SharedContainerStore.storageContainerRoot' in body, accessor
    assert 'containerURL(' not in body, accessor
app = (repo / 'src/ios/MinisApp.swift').read_text()
assert 'let container = fm.containerURL(forSecurityApplicationGroupIdentifier: "group.com.openminis.app")!' not in app
assert 'guard SharedContainerStore.appGroupContainer != nil else {' in app
print('PASS: startup accessors and FileProvider registration handle missing groups')
