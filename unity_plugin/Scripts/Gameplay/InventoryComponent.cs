using System.Collections.Generic;
using UnityEngine;

namespace Gameplay
{
    /// Basit envanter: eşya adı -> adet. Ölümde DÜŞMEZ (GAME_DESIGN kararı 3).
    public class InventoryComponent : MonoBehaviour
    {
        public List<string> startingItems = new List<string>();

        readonly Dictionary<string, int> _items = new Dictionary<string, int>();

        void Awake()
        {
            foreach (var item in startingItems) Add(item, 1);
        }

        public void Add(string itemId, int count = 1)
        {
            if (string.IsNullOrEmpty(itemId) || count <= 0) return;
            _items.TryGetValue(itemId, out int cur);
            _items[itemId] = cur + count;
        }

        public bool Remove(string itemId, int count = 1)
        {
            if (!_items.TryGetValue(itemId, out int cur) || cur < count) return false;
            cur -= count;
            if (cur <= 0) _items.Remove(itemId); else _items[itemId] = cur;
            return true;
        }

        public int CountOf(string itemId) => _items.TryGetValue(itemId, out int c) ? c : 0;
    }
}
