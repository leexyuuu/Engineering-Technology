<template>
  <el-dropdown :show-timeout="100" trigger="click">
    <el-button plain>
      typeOptions({{ type+"" }})
      <i class="el-icon-caret-bottom el-icon--right" />
    </el-button>
    <el-dropdown-menu slot="dropdown" class="no-padding">
      <el-dropdown-item>
        <el-radio-group v-model="status" style="padding: 10px;">
          <el-radio :label="'吐槽'" >
            1
          </el-radio>
          <el-radio :label="'问答'">
            2
          </el-radio>
          <el-radio :label="'找搭子'">
            3
          </el-radio>
          <el-radio :label="'闲置'">
            4
          </el-radio>
          <el-radio :label="'活动'">
            5
          </el-radio>
        </el-radio-group>
      </el-dropdown-item>
    </el-dropdown-menu>
  </el-dropdown>
</template>

<script>
export default {
  props: {
    value: {
      type: Int,
      default: 1
    }
  },
  data() {
    return {
      typeOptions: [
        { key: '1', name: '吐槽' },
        { key: '2', name: '问答' },
        { key: '3', name: '找搭子' },
        { key: '4', name: '闲置' },
        { key: '5', name: '二手' },
    
      ]
    }
  },
  computed: {
    type: {
      get() {
        return this.value
      },
      set(val) {
        this.$emit('input', val)
      }
    }
  }
}
</script>
